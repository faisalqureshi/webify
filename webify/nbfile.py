import util2 as util
#import os
from nbconvert.exporters import HTMLExporter
import logging
import json
import re
#import markdown

class JupyterNotebookSettings:
    def __init__(self, dir, rc):
        self.logger = util.WebifyLogger.get('nb')
        
        self.dir = dir

        # default behavior
        self.copy_source = False
        self.render_html = True

        self.logger.info('Reading Jupyter Notebook Settings: %s' % self.dir.get_fullpath())

        ipynb_settings = rc.value('jupyternotebooks')
        if ipynb_settings == None:
            self.logger.debug(' Using defaults.')

        if isinstance(ipynb_settings, dict):
            self.load_folder_specific_settings(ipynb_settings)
        elif isinstance(ipynb_settings, list):
            self.logger.warning('Jupyter Notebook Settings: (%s):\n File specific settings not supported.' % self.dir.get_fullpath())
        else:
            pass

        self.logger.info(' - render-html: %s' % self.render_html)
        self.logger.info(' - copy-source: %s' % self.copy_source)

    def load_folder_specific_settings(self, ipynb_settings):
        self.logger.debug(' Found')

        try:
            copy_source = ipynb_settings['copy-source']
            assert(isinstance(copy_source, bool))
            self.copy_source = copy_source
        except:
            self.logger.warning('Jupyter Notebook Settings: (%s):\n Error reading copy-source.  Using default value.' % self.dir.get_fullpath())

        try:
            render_html = ipynb_settings['render-html']
            assert(isinstance(copy_source, bool))
            self.render_html = render_html
        except:
            self.logger.warning('Jupyter Notebook Settings: (%s):\n Error reading render-html.  Using default value.' % self.dir.get_fullpath())

        if ((copy_source or render_html) == False):
            self.logger.warning('Jupyter Notebook Settings: (%s):\n Both copy-source and render-html are False.  Forcing render-html to True.' % self.dir.get_fullpath())
            self.render_html = True

class JupyterNotebookfile:

    def __init__(self, filepath):
        self.logger = util.WebifyLogger.get('nb')
        self.filepath = filepath

        self.heading = None
        self.lesson_plan = ''


    def get_metadata(self):
        f = open(self.filepath,)
        data = json.load(f)
        self.process_cells(data['cells'])
        return {

        }

    def get_html_buffer(self):
        try:
            exporter = HTMLExporter()
            buffer, _ = exporter.from_filename(self.filepath)
            
            self.logger.info('Jupyter Notebook rendered as html: %s' % self.filepath)
        except:
            self.logger.warning('Jupyter Notebook conversion failed: %s' % self.filepath)
            return ''

        return buffer

    def process_cell(self, source):
        """
        Picks the first level-1 heading.  All subsequent headings are ignored.
        """
        collect_lesson_plan = False 

        for line in source:
            if collect_lesson_plan:
                self.lesson_plan += line
                continue

            heading_match = re.match('(^# [a-zA-Z0-9 ]+$)', line)
            if not heading_match == None:
                self.heading = heading_match[0]
                print(f'Found heading: {self.heading}')
                break

            lesson_match = re.match('(^## Lesson Plan$)', line)
            if not lesson_match == None:
                print(f'Found {lesson_match[0]}')
                collect_lesson_plan = True

    def process_cells(self, cells):
        print(f'{len(cells)} cells found.')
        
        i = 1
        for cell in cells:
            if not cell['cell_type'] == 'markdown':
                print(f'Ignoring cell {i}')
            else:
                print(f'Processing cell {i}')
                self.process_cell(cell['source'])
            i = i + 1

        print(self.heading)
        print(self.lesson_plan)
#        print(markdown.markdown(self.lesson_plan))

# def JupyterNotebookToHTML(filename, filepath, dest_filepath):
#     logger = util.WebifyLogger.get('webify')

#     try:
#         from nbconvert.exporters import HTMLExporter
#         exporter = HTMLExporter()
#         output, resources = exporter.from_filename(filepath)
#         open(dest_filepath, mode='w', encoding='utf-8').write(output)
#         if util.WebifyLogger.is_info(logger):
#             logger.info('    Compiled.')
#         else:
#             util.WebifyLogger.get('compiled').info('Compiled %s to %s' % (filename, dest_filepath))
#         logger.info('    Saved')
#     except:
#         logger.warning('Jupyter notebook conversion failed: %s' % dest_filepath)
#         return Failed, 'Copy Failed'

#     return True, 'Copied'
