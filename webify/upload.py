import util2 as util
import subprocess

class UploadScript:
    def __init__(self, shell_script):
        self.logger = util.WebifyLogger.get('upload')
        self.shell_script = shell_script
        self.logger.debug('Upload script: %s' % self.shell_script)

    def run(self):
        if self.shell_script == None:
            self.logger.info('No upload shell script specified.')
            return

        try:
            self.logger.info('Running upload shell script: %s' % self.shell_script)
            x = subprocess.run([self.shell_script])
            x.check_returncode()           
        except subprocess.CalledProcessError as e:
            self.logger.warning('Upload shell script failed: %s (%s)' % (self.shell_script, e))
        except:
            self.logger.warning('Upload shell script failed: %s' % (self.shell_script))
