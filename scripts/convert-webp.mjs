// scripts/convert-webp.mjs
import { createClient } from "@supabase/supabase-js";
import sharp from "sharp";
import { execSync } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";
import "dotenv/config";

const MODEL_FOLDERS = {
  dynamic: "BiRefNet_dynamic",
  hr: "BiRefNet_HR",
  rmbg20: "RMBG-2.0",
};

const availableModels = Object.entries(MODEL_FOLDERS)
  .filter(([name, folder]) => {
    const dir = path.join("scripts", "models", folder);
    const weights = path.join(dir, "model.safetensors");
    return fs.existsSync(dir) && fs.existsSync(weights);
  })
  .map(([name]) => name);

if (!availableModels.length) {
  console.error("Hic bir model bulunamadi. scripts/models altina indir.");
  process.exit(1);
}

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
const modelArg = getArg("model", "dynamic");
const updateDB = process.argv.includes("--update-db");

if (!availableModels.includes(modelArg)) {
  console.error(
    `Model '${modelArg}' bulunamadi. Hazir modeller: ${availableModels.join(", ")}`
  );
  process.exit(1);
}

const refineScript = path.resolve("scripts", "refine_bg.py");
const tmpDir = os.tmpdir();

// --- Supabase ---
const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
const storage = supabase.storage.from(BUCKET);
const publicBase = `${SUPABASE_URL}/storage/v1/object/public/${BUCKET}/`;

// --- LIST ---
const listOnce = async (pfx) => {
  const { data, error } = await storage.list(pfx || "", { limit: 1000 });
  if (error) throw error;
  return (data || []).filter((f) => /\.(jpe?g|png)$/i.test(f.name));
};

// --- DOWNLOAD ---
const downloadFile = async (itemPath) => {
  const { data, error } = await storage.download(itemPath);
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

// --- CALL REFINE ---
async function refineBg(buf, tmpName) {
  const inputPath = path.join(tmpDir, `${tmpName}.jpg`);
  const outputPath = path.join(tmpDir, `${tmpName}-refined.png`);
  fs.writeFileSync(inputPath, buf);

  try {
    execSync(`python "${refineScript}" "${inputPath}" "${outputPath}"`, {
      stdio: "inherit",
    });
  } catch (err) {
    console.error("Arka plan iyilestirme hatasi:", err.message);
    throw err;
  }

  const refined = fs.readFileSync(outputPath);
  fs.unlinkSync(inputPath);
  fs.unlinkSync(outputPath);
  return refined;
}

// --- MAIN ---
(async () => {
  const files = await listOnce(prefix);
  if (!files.length) {
    console.log("Islenecek dosya yok.");
    return;
  }

  for (const f of files) {
    const srcPath = prefix ? `${prefix}/${f.name}` : f.name;
    const dstPath = srcPath.replace(/\.(jpe?g|png)$/i, ".webp");
    console.log("BUCKET:", BUCKET, "SRC PATH:", srcPath);

    const buf = await downloadFile(srcPath);
    if (!buf) continue;

    const refinedBuf = await refineBg(buf, Date.now().toString());
    const webpBuf = await sharp(refinedBuf).webp({ quality }).toBuffer();

    await uploadFile(dstPath, webpBuf);
    await removeFile(srcPath);

    if (updateDB) {
      const oldUrl = publicBase + srcPath;
      const newUrl = publicBase + dstPath;

      // 1. DENEME: Tam URL eşleşmesi
      let { data, error } = await supabase
        .from(PRODUCTS_TABLE)
        .update({ [IMAGE_COLUMN]: newUrl })
        .eq(IMAGE_COLUMN, oldUrl)
        .select();

      if (error) {
        console.error(`❌ DB Update Hatası (Tam URL):`, error.message);
      } else if (!data || data.length === 0) {
        // 2. DENEME: Tam URL bulunamadıysa, PATH ile 'ilike' araması yap
        // Örn: veritabanında domain farklı olabilir ama 'araclar/...' aynıdır.
        console.log(`⚠️ Tam URL eşleşmedi, Path ile deneniyor: %${srcPath}`);
        
        const { data: retryData, error: retryError } = await supabase
            .from(PRODUCTS_TABLE)
            .update({ [IMAGE_COLUMN]: newUrl })
            .ilike(IMAGE_COLUMN, `%${srcPath}`) // <-- GEVŞEK EŞLEŞME (Contains/EndsWith)
            .select();
            
        if (retryError) {
            console.error(`❌ DB Update Hatası (Path Fallback):`, retryError.message);
        } else if (!retryData || retryData.length === 0) {
            console.warn(`⚠️ İKİ DENEMEDE DE BULUNAMADI! Manuel kontrol et.`);
            console.warn(`   Aranan Path: ${srcPath}`);
        } else {
            console.log(`✅ DB Güncellendi (Path Match ile): ${srcPath}`);
        }

      } else {
        console.log(`✅ DB Güncellendi (Tam Match): ${srcPath}`);
      }
    }

    console.log(`✅ Dosya Dönüştürüldü: ${srcPath} -> ${dstPath}`);
  }
})();
