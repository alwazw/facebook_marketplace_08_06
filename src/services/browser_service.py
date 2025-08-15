import asyncio
from typing import List, Dict
from playwright.async_api import Page, BrowserContext
from src.models import FacebookAccount

class BrowserService:
    """
    A service to encapsulate all browser automation logic using Playwright.
    """

    def __init__(self, user_data_dir: str, persistent: bool = True):
        self.playwright = None
        self.browser_context: BrowserContext | None = None
        self.page: Page | None = None
        self.user_data_dir = user_data_dir
        self.persistent = persistent

    async def start(self):
        """
        Starts the playwright driver and launches a browser context.
        It can be persistent or non-persistent based on the `persistent` flag.
        """
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()

        if self.persistent:
            self.browser_context = await self.playwright.chromium.launch_persistent_context(
                self.user_data_dir,
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
        else:
            browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            self.browser_context = await browser.new_context()

        self.page = self.browser_context.pages[0] if self.browser_context.pages else await self.browser_context.new_page()
        await self.page.set_viewport_size({"width": 1920, "height": 1080})

    async def close(self):
        """
        Closes the browser context and stops the playwright driver.
        """
        if self.browser_context:
            await self.browser_context.close()
        if self.playwright:
            await self.playwright.stop()

    async def set_cookies(self, cookies: list):
        """Adds cookies to the browser context."""
        if cookies:
            await self.browser_context.add_cookies(cookies)
            print(f"Added {len(cookies)} cookies.")

    async def verify_login(self) -> bool:
        """
        Verifies that the user is logged in by checking for a known element.
        """
        print("Verifying login status...")
        await self.page.goto("https://www.facebook.com/", wait_until="networkidle")

        print(f"Page title: {await self.page.title()}")
        print(f"Page URL: {self.page.url}")

        try:
            print("Page content:")
            print(await self.page.content())
        except Exception as e:
            print(f"Could not get page content: {e}")

        try:
            account_menu_selector = "div[aria-label='Account Controls and Settings']"
            await self.page.wait_for_selector(account_menu_selector, timeout=10000)
            print("Login verified successfully.")
            return True
        except Exception:
            print("Login verification failed.")
            await self.page.screenshot(path="login_verification_failed.png")
            return False

    async def get_unanswered_messages(self) -> List[dict]:
        """
        Navigates to the messages page and scrapes unanswered messages.
        Returns a list of conversation details for unanswered threads.
        """
        print("Navigating to messages page...")
        await self.page.goto("https://www.facebook.com/messages/t/", wait_until="networkidle")

        conversation_list_selector = "div[aria-label='Chats']"
        await self.page.wait_for_selector(conversation_list_selector, timeout=15000)

        # A more specific selector for individual threads. Facebook uses roles for accessibility.
        # This selector looks for links within the 'Chats' container.
        conversation_thread_selector = "a[href^='/messages/t/']"

        threads = await self.page.query_selector_all(conversation_thread_selector)
        print(f"Found {len(threads)} conversation threads.")

        unanswered_conversations = []

        for thread in threads:
            try:
                href = await thread.get_attribute('href')
                if not href:
                    continue

                conversation_id = href.split('/')[-2]

                # Strategy 1: Check for a visual 'Unread' indicator. This is often reliable.
                unread_indicator_selector = "div[aria-label='Unread']"
                unread_indicator = await thread.query_selector(unread_indicator_selector)

                # Let's try to get the last message text as well.
                last_message_text = ""
                # This selector will need to be very specific to the message preview text.
                # It's likely a span within the link.
                last_message_text_selector = "span"
                last_message_spans = await thread.query_selector_all(last_message_text_selector)
                if len(last_message_spans) > 1:
                    last_message_text = await last_message_spans[-1].text_content() or ""

                if unread_indicator:
                    unanswered_conversations.append({
                        "conversation_id": conversation_id,
                        "thread_element": thread,
                        "last_message_text": last_message_text.strip()
                    })
                    continue # Move to the next thread

                # Strategy 2: Check the last message text preview.
                # If it starts with "You:", it's a message sent by us.
                # This is a fallback in case the 'Unread' indicator isn't present.
                last_message_text_selector = "span" # This is a generic selector, might need refinement

                # We need to get the text content of the last message preview.
                # This requires finding the right element within the thread.
                # Let's assume the last message text is in a span inside the thread link.
                last_message_spans = await thread.query_selector_all(last_message_text_selector)
                last_message_text = ""
                if len(last_message_spans) > 1: # Often there are multiple spans, one for name, one for message
                    last_message_text = await last_message_spans[-1].text_content()

                if last_message_text and not last_message_text.strip().startswith("You:"):
                    # This is likely an unanswered message, but it's less certain than the unread indicator.
                    # For now, let's be conservative and only rely on the unread indicator.
                    # In a future iteration, we could add a more complex logic here.
                    pass

            except Exception as e:
                print(f"Could not process a thread: {e}")

        print(f"Found {len(unanswered_conversations)} unanswered conversations.")
        return unanswered_conversations

    async def send_reply(self, conversation: Dict, message: str):
        """
        Sends a reply to a specific conversation.
        'conversation' is a dictionary containing the thread_element.
        """
        thread_element = conversation.get("thread_element")
        if not thread_element:
            print("Error: thread_element not found in conversation object.")
            return

        try:
            print(f"Replying to conversation {conversation.get('conversation_id')}")
            await thread_element.click()

            # Wait for the message input field to be ready.
            # Facebook uses a div with role='textbox' for the message input.
            message_input_selector = "div[aria-label='Message'][role='textbox']"
            await self.page.wait_for_selector(message_input_selector, timeout=10000)

            # Type the message
            await self.page.locator(message_input_selector).fill(message)

            # Click the send button
            # The send button is often an SVG inside a div with a specific aria-label.
            send_button_selector = "div[aria-label='Press Enter to send']"
            await self.page.locator(send_button_selector).click()

            print(f"Successfully sent reply: {message}")

        except Exception as e:
            print(f"Failed to send reply: {e}")
            await self.page.screenshot(path=f"send_reply_failed_{conversation.get('conversation_id')}.png")

    async def logout(self):
        """
        Logs out of the Facebook account.
        """
        print("Logging out...")
        try:
            # The selector for the account menu might be something like:
            account_menu_selector = "div[aria-label='Account Controls and Settings']"
            await self.page.locator(account_menu_selector).click()

            # The logout button is usually inside the menu and might have a specific test id or role.
            # Using a selector that looks for a div with a role of button containing the text 'Log Out'.
            logout_button_selector = "div[role='button']:has-text('Log Out')"
            await self.page.locator(logout_button_selector).click()

            # Wait for the page to redirect to a page that indicates we are logged out.
            # The URL might contain 'login' or it might be the homepage but with login fields.
            await self.page.wait_for_selector("input[name='email']", timeout=15000)
            print("Logout successful.")
        except Exception as e:
            print(f"Logout failed: {e}")
            await self.page.screenshot(path="logout_failed.png")
            raise Exception("Logout failed. Check screenshot 'logout_failed.png' for details.")
