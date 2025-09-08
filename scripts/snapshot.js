// scripts/snapshot.js
import fs from "fs";
import path from "path";
import fetch from "node-fetch";
import puppeteer from "puppeteer";

const BASE_URL = "https://xn--alnrm-o4abc.com"; // sitenin ana adresi
const SITEMAP_URL = `${BASE_URL}/sitemap.xml`;

async function main() {
    // 1. Sitemap indir
    const res = await fetch(SITEMAP_URL);
    const xml = await res.text();

    // 2. URL listesi çıkar
    const urls = [...xml.matchAll(/<loc>(.*?)<\/loc>/g)].map(m => m[1]);

    console.log(`Toplam ${urls.length} URL bulundu`);

    // 3. Puppeteer başlat
    const browser = await puppeteer.launch({
        headless: "new",
        args: ["--no-sandbox", "--disable-setuid-sandbox"],
    });

    const page = await browser.newPage();

    for (const url of urls) {
        try {
            console.log("Snapshot alınıyor:", url);
            await page.goto(url, {waitUntil: "networkidle2", timeout: 60000});
            const html = await page.content();

            // 4. Path'i çıkar, klasör yapısını koru
            let relPath = url.replace(BASE_URL, "").replace(/^\/+/, "");
            if (!relPath) relPath = "index"; // ana sayfa için

            const filePath = path.join("public", "prerender", relPath + ".html");

            // klasör oluştur
            fs.mkdirSync(path.dirname(filePath), {recursive: true});
            fs.writeFileSync(filePath, html, "utf8");
        } catch (err) {
            console.error("Hata:", url, err.message);
        }
    }

    await browser.close();
    console.log("Snapshot tamamlandı.");
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
