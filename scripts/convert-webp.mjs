// node scripts/convert-webp.mjs path1.jpg path2.jpg ...
import 'dotenv/config';
import {createClient} from '@supabase/supabase-js';
import {ImagePool} from '@squoosh/lib';

const supabase = createClient(
    process.env.SUPABASE_URL,
    process.env.SUPABASE_SERVICE_ROLE_KEY
);

const BUCKET = process.env.PRODUCT_IMAGE_BUCKET || 'product-images';

async function convertOne(path) {
    // 1) indir
    const {data, error} = await supabase.storage.from(BUCKET).download(path);
    if (error) throw new Error(`download fail: ${path} → ${error.message}`);
    const buf = new Uint8Array(await data.arrayBuffer());

    // 2) webp encode (lokal WASM, dışarıya istek yok)
    const pool = new ImagePool(1);
    const img = pool.ingestImage(buf);
    await img.encode({webp: {quality: 72, effort: 5}}); // agresifse quality 60–75 arası dene
    const webp = await img.encodedWith.webp;
    await pool.close();
    if (!webp) throw new Error(`encode fail: ${path}`);

    // 3) upload
    const newPath = path.replace(/\.[a-z0-9]+$/i, '.webp');
    const {error: upErr} = await supabase.storage
        .from(BUCKET)
        .upload(newPath, new Blob([webp.binary], {type: 'image/webp'}), {upsert: true});
    if (upErr) throw new Error(`upload fail: ${newPath} → ${upErr.message}`);

    // 4) public url + DB update (slug = dosya adı .webp’siz)
    const {data: pub} = supabase.storage.from(BUCKET).getPublicUrl(newPath);
    const publicUrl = pub?.publicUrl || null;
    const slug = newPath.split('/').pop()?.replace(/\.webp$/i, '');

    if (slug && publicUrl) {
        const {error: dbErr} = await supabase.from('products').update({image_url: publicUrl}).eq('slug', slug);
        if (dbErr) throw new Error(`db update fail (${slug}): ${dbErr.message}`);
    }

    // 5) eski dosyayı sil
    await supabase.storage.from(BUCKET).remove([path]);

    return {path, newPath, publicUrl};
}

async function main() {
    const paths = process.argv.slice(2);
    if (!paths.length) {
        console.error('Usage: node scripts/convert-webp.mjs <bucket/path1.jpg> <bucket/path2.png> ...');
        process.exit(1);
    }
    const out = [];
    for (const p of paths) {
        try {
            console.time(p);
            const r = await convertOne(p);
            console.timeEnd(p);
            out.push({ok: true, ...r});
        } catch (e) {
            out.push({ok: false, path: p, error: e.message});
        }
    }
    console.log(JSON.stringify({results: out}, null, 2));
}

main().catch(e => {
    console.error(e);
    process.exit(1);
});
