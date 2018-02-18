
// TODO:
// timeout = int(options.get("timeout", default_timeout))
default_timeout = 60

// JS entry point for third party scan.
module.exports = {
  scan: async (browser, page) => {
    const html = await page.content()
    return {html: html}
  }
}
