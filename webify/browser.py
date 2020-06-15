import webbrowser
import util2 as util
import sys

class BrowserController:
    def __init__(self):
        self.logger = util.WebifyLogger.get('browser')
        
        self.browser = self.check_if_available(self.logger)
        self.url = None
        self.enabled = True if self.browser else False

    @staticmethod
    def check_if_available(logger, browser_name=None):
        browser = None
        try:
            browser = webbrowser.get(browser_name)
            logger.info('Using live browser: %s' % 'default' if browser_name==None else browser_name)
            if not browser:
                raise ValueError
        except webbrowser.Error as err:
            logger.warning('Cannot create live browser: %s (%s)' % ('default' if browser_name==None else browser_name, err))            
        except ValueError as err:
            logger.warning('Cannot create live browser: %s (%s)' % ('default' if browser_name==None else browser_name, err))
        return browser

    def enable(self):
        if not self.browser:
            self.logger.warning('No live browser avaialable.  Cannot enable live viewing')
            return
        self.enabled = True

    def disable(self):
        self.enabled = False

    def toggle(self):
        if not self.browser:
            self.logger.warning('No live browser avaialable.  Cannot enable live viewing')
            return
        self.enabled = not self.enabled
        self.logger.critical('Browser referesh turned %s' % ('on' if self.enabled else 'off'))

    def set_url(self, url):
        if not self.browser:
            self.logger.warning('No live browser avaialable.  Cannot enable live viewing')
            return

        self.url = url
        self.logger.critical('Watching %s' % url)

    def refresh(self):
        if self.enabled and self.browser:
            if self.url:
                try:
                    self.browser.open(self.url, new=0, autoraise=False)
                    self.logger.debug('Success opening url %s' % self.url)
                except:
                    self.logger.warning('Cannot open url %s' % self.url)
            else:
                self.logger.warning('Cannot refresh browser.  No url specified.')
        else:
            self.logger.debug('Live browser: enabled=%s, browser=%s' % (self.enabled, self.browser))

if __name__ == '__main__':
    print('Webify browser check')
    print('Use this command to see if webbrowser is properly setup: python -m webbrowser -t "http://www.python.org"')
    print('')

    logger = util.WebifyLogger.get('browser')
    if len(sys.argv) != 2:
        print('Getting default browser')
        browser = BrowserController.check_if_available(logger)
    else:
        print('Getting browser: %s' % sys.argv[1])
        browser = BrowserController.check_if_available(logger, sys.argv[1])

    if browser:
        print('Success')
    else:
        print('Failure')
