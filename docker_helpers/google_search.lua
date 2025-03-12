function main(splash, args)
    -- Set user agent to mimic a real browser
    splash:set_user_agent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    -- Set viewport size like a real desktop
    splash:set_viewport_size(1366, 768)
    
    -- More realistic browser behavior
    splash:set_custom_headers({
        ["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        ["Accept-Language"] = "en-US,en;q=0.9",
        ["Accept-Encoding"] = "gzip, deflate, br",
        ["Connection"] = "keep-alive",
        ["Upgrade-Insecure-Requests"] = "1",
        ["Sec-Fetch-Dest"] = "document",
        ["Sec-Fetch-Mode"] = "navigate",
        ["Sec-Fetch-Site"] = "none",
        ["Sec-Fetch-User"] = "?1"
    })
    
    -- Enable JavaScript
    splash.js_enabled = true
    
    -- Enable private mode to avoid cookie tracking
    splash.private_mode_enabled = true
    
    -- Load the page
    local ok, reason = splash:go(args.url)
    if not ok then
        splash:log("Failed to load the page: " .. reason)
        return {error = reason}
    end
    
    -- Wait for page to load
    splash:wait(3)
    
    -- Scroll down slowly to trigger any lazy loading and appear more human-like
    for i = 1, 10 do
        splash:evaljs("window.scrollBy(0, 300)")
        splash:wait(0.3 + math.random() * 0.5)  -- Random wait time
    end
    
    -- Wait a bit more to ensure everything is loaded
    splash:wait(2)
    
    -- Check if Google is showing a captcha
    local has_captcha = splash:evaljs([[
        (document.body.innerText.indexOf('captcha') > -1) || 
        (document.body.innerText.indexOf('unusual traffic') > -1) ||
        (document.title.indexOf('unusual traffic') > -1)
    ]])
    
    if has_captcha == true then
        splash:log("CAPTCHA detected!")
        return {
            html = splash:html(),
            has_captcha = true
        }
    end
    
    -- Return the content and screenshot for debugging
    return {
        html = splash:html(),
        png = splash:png(),
        har = splash:har(),
        has_captcha = false
    }
end
