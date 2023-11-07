import util2 as util
#import os
from nbconvert.exporters import HTMLExporter
import logging
import json
import re
import pypandoc

class JupyterNotebookSettings:
    def __init__(self, dir, rc):
        self.logger = util.WebifyLogger.get('nb-settings')
        
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
        self.title = None
        self.lesson_plan = None
        self.loaded = False

    def load(self):
        try:
            self.logger.debug('Loading ipynb: %s' % self.filepath)
            f = open(self.filepath, encoding='utf-8')
            data = json.load(f)
            self.process_cells(data['cells'])
            self.loaded = True
        except ValueError as err:
            print('JSON parsing error:')
            print(err)
            self.logger.warning('Failed loading ipynb: %s' % self.filepath)
        except:
            self.logger.warning('Failed loading ipynb: %s' % self.filepath)
        
        return self.loaded

    def get_metadata(self):
        assert(self.loaded)

        pdoc_args =  ['--mathjax','--highlight-style=pygments']
        try:
            if isinstance(self.lesson_plan, str):
                lesson_plan = pypandoc.convert_text(self.lesson_plan, to='html', format='md', extra_args=pdoc_args)
            else:
                lesson_plan = self.lesson_plan
        except:
            self.logger.warning('Failed converting lesson plan to html using pandoc: %s' % self.filepath)
            lesson_plan = self.lesson_plan

        # print(self.title)
        # print(lesson_plan)

        return {
            'title': self.title,
            'lesson_plan': lesson_plan
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

    def process_cell(self, source, cell_id):
        """
        Picks the first level-1 heading.  All subsequent headings are ignored.
        """
        title = None 
        lesson_plan = None

        for line in source:
            if isinstance(lesson_plan, str):
                lesson_plan += line
                continue

            if self.title == None:
                title_match = re.match('(^# [a-zA-Z0-9 ]+$)', line)
                if not title_match == None:
                    title = title_match[0][2:]
                    self.logger.debug(f'Found heading in cell {cell_id}: {title}')
                    break

            if self.lesson_plan == None:
                lesson_match = re.match('(^## Lesson Plan$)', line)
                if not lesson_match == None:
                    self.logger.debug(f'Found {lesson_match[0]} in cell {cell_id}')
                    lesson_plan = ''

        return title, lesson_plan

    def process_cells(self, cells):
        self.logger.debug(f'{len(cells)} cells found.')
        
        i = 1
        for cell in cells:
            if isinstance(self.title, str) and isinstance(self.lesson_plan, str):
                break
            if not cell['cell_type'] == 'markdown':
                continue

            title, lesson_plan = self.process_cell(cell['source'], i)
            if isinstance(title, str):
                self.title = title
            if isinstance(lesson_plan, str):
                self.lesson_plan = lesson_plan            
                self.logger.debug(self.lesson_plan)
            
            i = i + 1

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
