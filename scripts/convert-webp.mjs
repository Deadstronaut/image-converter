import { createClient } from "@supabase/supabase-js";
import sharp from "sharp";
import fs from "fs";
import path from "path";

// env kontrolü
const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_ROLE_KEY = process.env.SERVICE_ROLE_KEY;
const BUCKET = process.env.BUCKET;
const PRODUCTS_TABLE = process.env.PRODUCTS_TABLE || "products";
const IMAGE_COLUMN = process.env.IMAGE_COLUMN || "image_url";
if (!SUPABASE_URL || !SERVICE_ROLE_KEY || !BUCKET) {
  console.error("Eksik env: SUPABASE_URL, SERVICE_ROLE_KEY, BUCKET");
  process.exit(1);
}

// argümanlar
const getArg = (n, d = null) => {
  const i = process.argv.indexOf(`--${n}`);
  return i > -1 ? process.argv[i + 1] : d;
};
const prefix = (getArg("prefix", "") || "").replace(/^\/|\/$/g, "");
const quality = parseInt(getArg("quality", "82"), 10);
const updateDB = process.argv.includes("--update-db");

// supabase istemcisi
const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
const storage = supabase.storage.from(BUCKET);
const publicBase = `${SUPABASE_URL}/storage/v1/object/public/${BUCKET}/`;

const tmpDir = "./input";
fs.mkdirSync(tmpDir, { recursive: true });

const listOnce = async (pfx) => {
  const { data, error } = await storage.list(pfx || "", { limit: 1000 });
  if (error) throw error;
  return (data || []).filter(f => /\.(jpe?g|png)$/i.test(f.name));
};

const downloadFile = async (pfx, name) => {
  const full = pfx ? `${pfx}/${name}` : name;
  const { data, error } = await storage.download(full);
  if (error) throw error;
  const buf = Buffer.from(await data.arrayBuffer());

  // 🔎 Debug
  console.log("DEBUG >>>", full, "size:", buf.length, "first20:", buf.slice(0,20).toString("hex"));

  const out = path.join(tmpDir, name);
  fs.writeFileSync(out, buf);
  return out;
};




const uploadFile = async (dstPath, buf) => {
  const { error } = await storage.upload(dstPath, buf, {
    contentType: "image/webp",
    upsert: true,
  });
  if (error) throw error;
};

const removeFile = async (srcPath) => {
  const { error } = await storage.remove([srcPath]);
  if (error) throw error;
};

(async () => {
  const files = await listOnce(prefix);
  if (!files.length) {
    console.log("Hiç dosya yok");
    return;
  }

  for (const f of files) {
    const srcPath = prefix ? `${prefix}/${f.name}` : f.name;
    const dstPath = srcPath.replace(/\.(jpe?g|png)$/i, ".webp");
    const localPath = await downloadFile(prefix, f.name);
    const webpBuf = await sharp(localPath).webp({ quality }).toBuffer();

    await uploadFile(dstPath, webpBuf);
    await removeFile(srcPath);

    if (updateDB) {
      const oldUrl = publicBase + srcPath;
      const newUrl = publicBase + dstPath;
      const { error } = await supabase
        .from(PRODUCTS_TABLE)
        .update({ [IMAGE_COLUMN]: newUrl })
        .eq(IMAGE_COLUMN, oldUrl);
      if (error) console.error("DB update err:", error.message);
    }

    console.log(`Dönüştürüldü: ${srcPath} → ${dstPath}`);
  }
})();





