import { createClient } from "@supabase/supabase-js";
import sharp from "sharp";
import { execSync } from "child_process";
import fs from "fs";
import path from "path";

// --- ENV ---
const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_ROLE_KEY = process.env.SERVICE_ROLE_KEY;
const BUCKET = process.env.BUCKET;
const PRODUCTS_TABLE = process.env.PRODUCTS_TABLE || "products";
const IMAGE_COLUMN = process.env.IMAGE_COLUMN || "image_url";
if (!SUPABASE_URL || !SERVICE_ROLE_KEY || !BUCKET) {
  console.error("Eksik env: SUPABASE_URL, SERVICE_ROLE_KEY, BUCKET");
  process.exit(1);
}

// --- ARGS ---
const getArg = (n, d = null) => {
  const i = process.argv.indexOf(`--${n}`);
  return i > -1 ? process.argv[i + 1] : d;
};
const prefix = (getArg("prefix", "") || "").replace(/^\/|\/$/g, "");
const quality = parseInt(getArg("quality", "82"), 10);
const updateDB = process.argv.includes("--update-db");

// --- Supabase ---
const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
const storage = supabase.storage.from(BUCKET);
const publicBase = `${SUPABASE_URL}/storage/v1/object/public/${BUCKET}/`;

// --- LIST ---
const listOnce = async (pfx) => {
  const { data, error } = await storage.list(pfx || "", { limit: 1000 });
  if (error) throw error;
  return (data || []).filter(f => /\.(jpe?g|png)$/i.test(f.name));
};

// --- DOWNLOAD ---
const downloadFile = async (path) => {
  const { data, error } = await storage.download(path);
  if (error) throw error;
  return Buffer.from(await data.arrayBuffer());
};

// --- UPLOAD ---
const uploadFile = async (dstPath, buf) => {
  const { error } = await storage.upload(dstPath, buf, {
    contentType: "image/webp",
    upsert: true,
  });
  if (error) throw error;
};

// --- REMOVE ---
const removeFile = async (srcPath) => {
  const { error } = await storage.remove([srcPath]);
  if (error) throw error;
};

// --- REMBG ---
async function removeBg(buf, tmpName) {
  const inPath = path.join("/tmp", tmpName + ".jpg");
  const outPath = path.join("/tmp", tmpName + ".png");
  fs.writeFileSync(inPath, buf);

  const cmd = [
    "rembg i",
    "--model isnet-general-use",
    "--alpha-matting",
    "--alpha-matting-foreground-threshold 200",
    "--alpha-matting-background-threshold 25",
    "--alpha-matting-erode-size 1",
    inPath,
    outPath,
  ].join(" ");

  execSync(cmd);
  return fs.readFileSync(outPath);
}

// --- MAIN ---
(async () => {
  const files = await listOnce(prefix);
  if (!files.length) {
    console.log("Hiç dosya yok");
    return;
  }
  for (const f of files) {
    const srcPath = prefix ? `${prefix}/${f.name}` : f.name;
    const dstPath = srcPath.replace(/\.(jpe?g|png)$/i, ".webp");
    console.log("BUCKET:", BUCKET, "SRC PATH:", srcPath);

    const buf = await downloadFile(srcPath);
    if (!buf) continue;

    const pngBuf = await removeBg(buf, Date.now().toString());
    const webpBuf = await sharp(pngBuf).webp({ quality }).toBuffer();

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

    console.log(`✅ ${srcPath} → ${dstPath}`);
  }
})();








