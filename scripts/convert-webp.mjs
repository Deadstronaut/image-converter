import { createClient } from "@supabase/supabase-js";
import { ImagePool } from "@squoosh/lib";

const env = (k, d=null)=>process.env[k] ?? d;
const SUPABASE_URL = env("SUPABASE_URL");
const SERVICE_ROLE_KEY = env("SERVICE_ROLE_KEY");
const BUCKET = env("BUCKET");
const PRODUCTS_TABLE = env("PRODUCTS_TABLE","products");
const IMAGE_COLUMN = env("IMAGE_COLUMN","image_url");

if(!SUPABASE_URL||!SERVICE_ROLE_KEY||!BUCKET){
  console.error("Missing env: SUPABASE_URL, SERVICE_ROLE_KEY, BUCKET"); process.exit(1);
}

const getArg=(n,def)=>{const i=process.argv.indexOf(`--${n}`);return i>-1?process.argv[i+1]:def};
const prefix = (getArg("prefix","")||"").replace(/^\/|\/$/g,"");
const quality = parseInt(getArg("quality","82"),10);
const updateDB = process.argv.includes("--update-db");

const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
const storage = supabase.storage.from(BUCKET);
const publicBase = `${SUPABASE_URL}/storage/v1/object/public/${BUCKET}/`;

const listOnce = async (pfx) => {
  const { data, error } = await storage.list(pfx || "", { limit: 1000, sortBy:{column:"name",order:"asc"} });
  if(error) throw error;
  return (data||[]).filter(f => f.name && /\.(jpe?g|png)$/i.test(f.name));
};

const downloadBuf = async (path) => {
  const { data, error } = await storage.download(path);
  if(error) throw error;
  const ab = await data.arrayBuffer();
  return Buffer.from(ab);
};

const uploadBuf = async (path, buf) => {
  const { error } = await storage.upload(path, buf, { contentType:"image/webp", upsert:true });
  if(error) throw error;
};

const removePath = async (path) => {
  const { error } = await storage.remove([path]);
  if(error) throw error;
};

(async () => {
  const files = await listOnce(prefix);
  if(!files.length){ console.log("No files"); return; }

  const pool = new ImagePool();
  const results = [];

  for (const f of files){
    const srcPath = prefix ? `${prefix}/${f.name}` : f.name;
    const dstPath = srcPath.replace(/\.(jpe?g|png)$/i, ".webp");

    const input = await downloadBuf(srcPath);
    const img = pool.ingestImage(input);
    await img.encode({ webp: { quality } });
    const webp = (await img.encodedWith.webp).binary;

    await uploadBuf(dstPath, webp);
    await removePath(srcPath);

    const oldUrl = publicBase + srcPath;
    const newUrl = publicBase + dstPath;

    if(updateDB){
      const { error } = await supabase.from(PRODUCTS_TABLE)
        .update({ [IMAGE_COLUMN]: newUrl })
        .eq(IMAGE_COLUMN, oldUrl);
      if(error) console.error("DB update err:", error.message);
    }

    results.push({ converted: srcPath, to: dstPath });
    console.log(JSON.stringify({ converted: srcPath, to: dstPath }));
  }

  await pool.close();
  console.log(JSON.stringify({ done: true, count: results.length }));
})();
