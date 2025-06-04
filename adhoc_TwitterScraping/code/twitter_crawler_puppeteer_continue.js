const puppeteer = require("puppeteer-core");
const fs = require("fs");

const accounts = [
  "0x_ultra", "0xWenMoon", "kickzeth", "waleswoosh", "blknoiz06",
  "beast_ico", "vohvohh", "0xNairolf", "thegreatola", "Deebs_DeFi"
];

function getSinceDate() {
  const since = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000);
  return since.toISOString().slice(0, 10);
}

async function run() {
  const browser = await puppeteer.connect({
    browserWSEndpoint: "wss://brd-customer-hl_b8ff289a-zone-myzone:u8r2tse6ag4o@brd.superproxy.io:9222",
  });
  console.log("Đã kết nối Bright Data Browser API...");

  for (const username of accounts) {
    const page = await browser.newPage();
    page.setDefaultNavigationTimeout(2 * 60 * 1000);

    const since = getSinceDate();
    const searchUrl = `https://twitter.com/search?q=from%3A${username}%20since%3A${since}&src=typed_query&f=live`;

    await page.goto(searchUrl, { waitUntil: "domcontentloaded" });
    console.log(`Đang cào tài khoản: ${username}`);

    try {
      await page.waitForSelector('article[data-testid="tweet"]', { timeout: 60000 });
    } catch (e) {
      console.log(`Không tìm thấy tweet nào cho ${username} hoặc bị chặn!`);
      await page.close();
      continue;
    }

    for (let i = 0; i < 30; i++) {
      await page.evaluate(() => window.scrollBy(0, 2000));
      await new Promise(r => setTimeout(r, 2000));
    }

    const tweets = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('article[data-testid="tweet"]')).map(el => ({
        url: el.querySelector('a[href*="/status/"]') ? el.querySelector('a[href*="/status/"]').href : '',
        content: el.innerText,
        time: el.querySelector('time') ? el.querySelector('time').getAttribute('datetime') : ''
      }));
    });

    const csvHeader = "username,time,url,content\n";
    const csvRows = tweets.map(t => 
      `"${username}","${t.time}","${t.url}","${t.content.replace(/\"/g, '\"\"')}"`
    );
    const fileName = `${username}_tweets_90days.csv`;
    fs.writeFileSync(fileName, csvHeader + csvRows.join("\n"), "utf8");
    console.log(`Đã lưu dữ liệu cho ${username} vào file ${fileName}`);

    await page.close();
  }

  await browser.close();
}

run().catch(err => {
  console.error("Đã xảy ra lỗi:", err);
});