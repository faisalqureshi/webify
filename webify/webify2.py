import argparse
import pprint as pp
import sys
import logging
import os
import util2 as util
from mdfile2 import MDfile
import pypandoc
import pystache
import yaml
import pathspec
import datetime
import markupsafe
import json
import rc as RenderingContext
import time_util as tm
import dirtree as dt
import dirstack as ds
from yamlfile import YAMLfile
from htmlfile import HTMLfile
from nbfile import JupyterNotebookfile, JupyterNotebookSettings
import time
import datetime
#import running as run

from globals import __version__

logfile = 'webify2.log'
ignorefile = '.webifyignore'

class Webify:
    def __init__(self):
        self.logger = util.WebifyLogger.get('main')
        self.rc = RenderingContext.RenderingContext()
        self.ignore = None
        self.dir_tree = dt.DirTree()
        self.dir_stack = ds.DirStack()
        self.next_run_time = None

    def set_renderer(self):
        if self.meta_data['renderer'] in [None, 'jinja2']:
            self.render = util.jinja2_renderer
        else:
            self.render = util.mustache_renderer
        
    def get_src(self):
        return self.srcdir

    def get_dest(self):
        return self.destdir

    def set_src(self, srcdir):
        self.srcdir = os.path.abspath(srcdir)
        if not os.path.isdir(self.srcdir):
            self.logger.critical('Source folder not found: %s' % srcdir)
            self.logger.critical('Nothing to do here.')
            raise ValueError('Error source folder')
        else:
            self.logger.info('Source folder found: %s' % srcdir)
            self.ignore = util.IgnoreList(srcdir=self.srcdir)
            self.ignore.read_ignore_file(os.path.abspath(os.path.join(srcdir, ignorefile)))

    def set_meta_data(self, meta_data):
        self.meta_data = meta_data
        self.set_renderer()
        self.rc.reset()
        self.rc.add(meta_data)

    def set_dest(self, destdir):
        self.destdir = os.path.abspath(destdir)

        if self.destdir == self.srcdir:
            raise ValueError('Destination folder is the same as source folder.  This is an icredibly bad idea.')

        r = util.make_directory(destdir)
        if not r:
            self.logger.critical('Cannot create destination folder: %s' % destdir)
            self.logger.critical('Nothing to do here.')
            raise ValueError('Error destination folder')
        else:
            self.logger.info('Destination directory %s: %s' % (r, destdir))

    def check_availability_(self, s, e, filepath):
        logger_availability = util.WebifyLogger.get('availability')

        ts, te = tm.parse(s), tm.parse(e)
        logger_availability.debug('%s - start: %s\nend: %s' % (filepath, ts, te))
        
        if not tm.check_valid_start_and_end(ts, te):
            logger_availability.warning('Availability start time is after end time: %s' % filepath)
            return False
        self.find_next_time_to_run(ts, te, filepath)
        v = tm.check_for_time_in_range(ts, te, self.meta_data['__time__'])
        logger_availability.debug('v: %s' % v)
        if v == 'error':
            self.logger.warning('Error reading availability times for %s' % filepath)
            return False
        return v

    def check_availability_md(self, mdfile):
        logger_availability = util.WebifyLogger.get('availability')

        logger_availability.debug('Checking availability (md) for %s' % mdfile.get_filepath())
        s, e = mdfile.get_availability()
        return self.check_availability_(s, e, mdfile.get_filepath())
        
    def check_ignore(self, filepath, ignore_info):
        logger_ignore = util.WebifyLogger.get('ignore')
        
        logger_ignore.debug('Ignore: checking ignore for %s' % filepath)

        try:
            v = ignore_info[filepath]['ignore']
            logger_ignore.debug('Ignore: ignore info for %s: %s' % (filepath, v))
            return v
        except:
            logger_ignore.debug('Ignore: found no ignore info for file %s' % filepath)
            return False

    def check_availability(self, filepath, availability):
        logger_availability = util.WebifyLogger.get('availability')
        
        logger_availability.debug('Checking availability for %s' % filepath)
        logger_availability.debug(pp.pformat(availability))

        try:
            s = availability[filepath]['start']
            e = availability[filepath]['end']
            return self.check_availability_(s, e, filepath)
        except:
            logger_availability.debug('Find no availability info for file %s' % filepath)
            return True

    def proc_partials(self, dir):
        data = {}
        if dir.partials:
            self.logger.info('Processing _partials ...')
            self.logger.info('Processing: %s' % dir.partials.get_fullpath())
            self.rc.push()

            # Load YAML
            if len(dir.partials.files['yaml']) > 0:
                self.logger.info('Processing  YAML files ...')
            else:
                self.logger.info('No YAML files found')
            for filename in dir.partials.files['yaml']:
                filepath = self.make_src_filepath(dir, os.path.join('_partials', filename))
                yaml_file = YAMLfile(filepath=filepath)
                yaml_file.load()
                self.rc.add(yaml_file.data)

            # Load HTML
            if len(dir.partials.files['html']) > 0:
                self.logger.info('Processing  HTML files ...')
            else:
                self.logger.info('No HTML files found')
            for filename in dir.partials.files['html']:
                filepath = self.make_src_filepath(dir, os.path.join('_partials', filename))
                html_file = HTMLfile(filepath)
                buffer = html_file.load().get_buffer()
                rendered_buf = self.render(template=buffer, render_filepath=filepath, context=self.rc.data(), src_filepath=filepath)
                data[filename.replace('.','_')] = markupsafe.Markup(rendered_buf)

            # Load Markdown
            if len(dir.partials.files['md']) > 0:
                self.logger.info('Processing  MD files ...')
            else:
                self.logger.info('No MD files found')
            args = { 'create-output-file': False, 
                     'ignore-times': self.meta_data['__ignore_times__'],
                     'pandoc-var': self.meta_data['pandoc-var'],
                     'pandoc-meta': self.meta_data['pandoc-meta'] }
            for filename in dir.partials.files['md']:  
                filepath = self.make_src_filepath(dir, os.path.join('_partials', filename))
                self.logger.info('Processing MD file: %s' % filepath)
                self.rc.push()
                md_file = MDfile(filepath=filepath, args=args)
                md_file = self.md_set_defaults(md_file)
                md_file.load(self.rc)
                ret_type, buffer, _ = md_file.convert(self.rc)
                self.rc.pop()
                if not ret_type == 'buffer':
                    self.logger.warning('Ignoring _partials file: %s' % filepath)
                else:
                    data[filename.replace('.','_')] = markupsafe.Markup(buffer)

            self.logger.info('... done processing folder %s' % dir.partials.get_fullpath())
            self.rc.pop()

            # Add collected data to parent's rendering context.   
            self.rc.add(data)
        else:
            self.logger.info('No _partials found')

    def proc_yaml(self, dir):
        if len(dir.files['yaml']) > 0:
            self.logger.info('Processing  YAML files...')
        else:
            self.logger.info('No YAML files found')
        
        for filename in dir.files['yaml']:
            filepath = self.make_src_filepath(dir, filename)
            yaml_file = YAMLfile(filepath=filepath)
            yaml_file.load()
            self.rc.add(yaml_file.data)
    
    def capture_list_of(self, dir, availability, ignore_info, file_type):
        list_files = []
        for filename in dir.files[file_type]:
            filepath = self.make_src_filepath(dir, filename)
            output_filepath = self.make_output_filepath(dir, filename)
            is_available = self.check_availability(filepath, availability)
            is_ignored = self.check_ignore(filepath, ignore_info)
            self.capture_dir_listing_information(list_files, filename, filename, is_available, is_ignored, filepath, output_filepath, file_type, obj=None, data=None)
        return list_files

    def capture_list_of_ipynb(self, dir, availability, ignore_info):

        ipynb_settings = JupyterNotebookSettings(dir, self.rc)

        list_files = []
        for filename in dir.files['ipynb']:
            filepath = self.make_src_filepath(dir, filename)
            output_filepath = self.make_output_filepath(dir, filename)
            converted_filename = os.path.splitext(filename)[0]+'.html'
            converted_output_filepath = os.path.splitext(output_filepath)[0]+'.html'
            is_available = self.check_availability(filepath, availability)
            is_ignored = self.check_ignore(filepath, ignore_info)

            if (not is_ignored) and is_available:
                if ipynb_settings.copy_source:
                    self.capture_dir_listing_information(list_files, filename, filename, is_available, is_ignored, filepath, output_filepath, 'ipynb', obj=None, data=None)
                if ipynb_settings.render_html:
                    nb_file = JupyterNotebookfile(filepath, ipynb_settings.execute_notebook or self.meta_data['execute_jupyter-notebook'])
                    nb_file.load()
                    self.capture_dir_listing_information(list_files, filename, converted_filename, is_available, is_ignored, filepath, converted_output_filepath, 'ipynb-html', obj=nb_file, data=nb_file.get_metadata())

        return list_files

    def capture_list_of_md(self, dir, availability, ignore_info):
        list_files = []
        for filename in dir.files['md']:
            filepath = self.make_src_filepath(dir, filename)
            output_filepath = self.make_output_filepath(dir, filename)
            is_available = self.check_availability(filepath, availability)
            is_ignored = self.check_ignore(filepath, ignore_info)

            # print('Y', filename, 'is_ignored', is_ignored, 'is_available', is_available)

            self.rc.push()
            
            args = { 'ignore-times': self.meta_data['__ignore_times__'],
                     'output-filepath': os.path.splitext(output_filepath)[0],
                     'output-fileext': '',
                     'pandoc-var': self.meta_data['pandoc-var'],
                     'pandoc-meta': self.meta_data['pandoc-meta'] }
            md_file = MDfile(filepath=filepath, args=args)
            md_file = self.md_set_defaults(md_file)
            loaded_ok = md_file.load(self.rc)
            # print('loaded_ok', loaded_ok)
            if loaded_ok:
                converted_output_filepath = md_file.make_output_filepath()
                converted_filename = os.path.split(converted_output_filepath)[1]
                should_process, reason, _, _ = self.md_inspect_frontmatter(md_file)
            else:
                converted_output_filepath = output_filepath
                converted_filename = filename

            # print('should_process', should_process)
            if (not is_ignored) and is_available and loaded_ok and should_process:
                # print('YY')
                if md_file.get_value('copy-source'):
                    self.capture_dir_listing_information(list_files, filename, filename, True, False, filepath, output_filepath, 'md-src', obj=None, data=None)

                self.capture_dir_listing_information(list_files, filename, converted_filename, True, False, filepath,converted_output_filepath, 'md', obj=md_file, data=md_file.get_yaml())
            else:
                # print('ZZ')
                if not should_process:
                    is_ignored = True if reason == 'ignore' else is_ignored
                    is_available = False if reason == 'not available' else is_available

                # print('is_ignored', is_ignored, 'is_available', is_available)

                self.capture_dir_listing_information(list_files, filename, converted_filename, is_available, is_ignored, filepath, converted_output_filepath, 'md', obj=None, data=None)

            self.rc.pop()
        return list_files

    def proc_files(self, dir, dir_list):
        for i in dir_list:
            src_filename = i['src_filename']
            filename = i['filename']
            filepath = i['filepath']
            is_available = i['is_available']
            is_ignored = i['is_ignored']
            output_filepath = i['output_filepath']
            file_type = i['file_type']

            # print('X', filename, file_type, 'is_ignored', is_ignored, 'is_available', is_available)
            if is_ignored:
                # if (filename == 'post3.html'):
                #       print('B', is_ignored)
                if util.WebifyLogger.is_info(self.logger):
                    self.logger.info('x-: %s' % src_filename) 
                else:
                    util.WebifyLogger.get('ignored').info('Ignored:\n   skipped %s' % filepath)
                x, m = util.remove_file(output_filepath)
                if x:
                    self.logger.info('    Removed %s' % output_filepath)
                else:
                    util.WebifyLogger.get('ignored').warning('   %s: (%s)' % (m, output_filepath))
                util.WebifyLogger.get('ignore').debug('Ignore: %s remove status (%s, %s)' % (output_filepath, x, m))
                continue

            if not is_available:
                if util.WebifyLogger.is_info(self.logger):
                    self.logger.info('x-: %s' % src_filename) 
                else:
                    util.WebifyLogger.get('available').info('Availability:\n   skipped %s' % filepath)
                x, m = util.remove_file(output_filepath)
                if x:
                    self.logger.info('    Removed %s' % output_filepath)
                else:
                    util.WebifyLogger.get('available').warning('   %s: (%s)' % (m, output_filepath))
                util.WebifyLogger.get('availability').debug('Availability: %s remove status (%s, %s)' % (output_filepath, x, m))
                continue

            self.logger.info('x+: %s -> %s' % (src_filename, filename))
            if file_type == 'html':
                self.convert_html(filename, filepath, output_filepath)
            elif file_type == 'misc':
                self.copy_misc(filename, filepath, output_filepath)
            elif file_type == 'ipynb':
                self.copy_misc(filename, filepath, output_filepath)
            elif file_type == 'ipynb-html':
                self.convert_ipynb(filename, filepath, output_filepath, i['obj'])
            elif file_type == 'md-src':
                self.copy_misc(filename, filepath, output_filepath)
            elif file_type == 'md':
                self.convert_md(filename, filepath, output_filepath, i['obj'])
                i['obj'] = None
            else:
                pass
            
    def convert_ipynb(self, filename, filepath, output_filepath, nb_file_obj):
        if os.path.isfile(output_filepath):
            if not self.meta_data['__ignore_times__'] and os.path.getmtime(filepath) <= os.path.getmtime(output_filepath):
                if util.WebifyLogger.is_info(self.logger):
                    util.WebifyLogger.get('not-compiled').info('    Destination file already exists.  Did not compile.')
                else:
                    util.WebifyLogger.get('not-compiled').info('Not compiled:\n   %s\n-> %s' % (filepath, output_filepath))
                return

        self.rc.push()
        self.rc.add({'__me__': filename})

        buffer = nb_file_obj.get_html_buffer()
        if util.save_to_file(output_filepath, buffer):
            if util.WebifyLogger.is_info(self.logger):
                self.logger.info('    Compiled.')
            else:
                util.WebifyLogger.get('compiled').info('Compiled: \n   %s \n-> %s' % (filepath, output_filepath))
            #self.logger.info('    Saved')
        else:
            self.logger.warning('Error saving Jupyter Notebook file %s' % output_filepath)

        self.rc.pop()

    def convert_html(self, filename, filepath, output_filepath):
        if os.path.isfile(output_filepath):
            if not self.meta_data['__ignore_times__'] and os.path.getmtime(filepath) <= os.path.getmtime(output_filepath):
                if util.WebifyLogger.is_info(self.logger):
                    util.WebifyLogger.get('not-compiled').info('    Destination file already exists.  Did not compile.')
                else:
                    util.WebifyLogger.get('not-compiled').info('Not compiled:\n   %s' % filepath)
                return

        self.rc.push()
        self.rc.add({'__me__': filename})

        html_file = HTMLfile(filepath)
        buffer = html_file.load().get_buffer()
        rendered_buf = self.render(template=buffer, render_filepath=filepath, context=self.rc.data(), src_filepath=filepath)
        if util.save_to_file(output_filepath, rendered_buf):
            if util.WebifyLogger.is_info(self.logger):
                self.logger.info('    Compiled.')
            else:
                util.WebifyLogger.get('compiled').info('Compiled: \n   %s \n-> %s' % (filepath, output_filepath))
            self.logger.info('    Saved')
        else:
            self.logger.warning('Error saving html file %s' % output_filepath)

        self.rc.pop()

    def md_set_defaults(self, md_file):
        if self.meta_data['renderer']:
            md_file.set_default('renderer', self.meta_data['renderer'])
        return md_file    

    def md_inspect_frontmatter(self, md_file):
        filepath = md_file.get_filepath()
        output_filepath = md_file.make_output_filepath()

        if md_file.get_value('ignore'):
            return False, 'ignore', filepath, output_filepath

        if not self.check_availability_md(md_file):
            return False, 'not available', filepath, output_filepath

        return True, None, None, None

    def convert_md(self, filename, filepath,  output_filepath, md_file_obj):
        self.rc.push()
        self.rc.add({'__me__': filename})

        status, saved_file, _ = md_file_obj.convert(self.rc)
        if status == 'file':
            if util.WebifyLogger.is_info(self.logger):
                self.logger.info('    Compiled.')
            else:
                util.WebifyLogger.get('compiled').info('Compiled: \n   %s \n-> %s' % (filepath, saved_file))
        elif status == 'exists':
            if util.WebifyLogger.is_info(self.logger):
                util.WebifyLogger.get('not-compiled').info('    Destination file already exists.  Did not compile.')
            else:
                util.WebifyLogger.get('not-compiled').info('Not compiled:\n   %s\n-> %s' % (filepath, output_filepath))
        else:
            saved_file = None
            self.logger.warning('Error processing %s' % filepath)
        
        self.rc.pop()
                    
    def capture_dir_listing_information(self, list_files, filename, converted_filename, is_available, is_ignored, filepath, output_filepath, file_type, obj, data):
        entry = {
            'src_filename': filename,
            'filename': converted_filename,
            'is_available': is_available,
            'is_ignored': is_ignored,
            'filepath': filepath,
            'output_filepath': output_filepath,
            'file_type': file_type,
            'obj': obj,
            'data': data,
            'ext': os.path.splitext(converted_filename)[1]
        }
        should_capture = is_available and (not is_ignored)
        self.logger.info('%s: %s' % (' +' if should_capture else ' -', filename))
        list_files.append(entry)

    def make_src_filepath(self, dir, filename):
        filepath =  os.path.join(dir.get_fullpath(), filename)
        return os.path.normpath(filepath)

    def make_output_filepath(self, dir, filename):
        output_filepath = os.path.join(self.destdir, dir.path, dir.name, filename)
        return os.path.normpath(output_filepath)
                
    def copy_misc(self, filename, filepath, output_filepath):
        v, s = util.process_file(filepath, output_filepath, self.meta_data['__force_copy__'])
        if not v:
            logger.warning('%s (%s)' % (filepath, s))
        else:
            if s == 'Exists':
                if util.WebifyLogger.is_info(self.logger):
                    util.WebifyLogger.get('not-copied').info('    Destination file already exists.  Did not copy.')
                else:
                    util.WebifyLogger.get('not-copied').info('Not copied:\n   %s\n-> %s' % (filepath, output_filepath))        

    def check_item_in_cur_folder(self, dir, item_name):
        cur_dir = dir.get_fullpath()
        item_name = os.path.expandvars(item_name)
        item_path = self.make_src_filepath(dir, item_name)
        item_dir = os.path.split(item_path)[0]
        if item_dir == cur_dir:
            if os.path.isfile(item_path):
                return True, 'file', item_path, item_name
            elif os.path.isdir(item_path):
                return True, 'dir', item_path, item_name
            else:
                return False, 'Not file or folder', '', item_name
        else:
            return False, 'Not in directory', '', item_name


    def load_ignore_info(self, dir):
        logger_ignore = util.WebifyLogger.get('ignore')
        logger_ignore.debug('Loading ignore info for folder %s' % dir.get_fullpath())

        ignore_info = {}
        x = self.rc.value('ignore')
        if not x:
            logger_ignore.debug('No ignore information found in folder %s' % dir.get_fullpath())
            return ignore_info
        else:
            logger_ignore.debug('Ignore information found in folder %s' % dir.get_fullpath())
            logger_ignore.debug(pp.pformat(x))

        try:
            if not isinstance(x, list):
                x = [x]
            for i in x:
                found, file_or_dir, item_path, item_name = self.check_item_in_cur_folder(dir, i['file'])
                logger_ignore.debug('Ignore: check %s: (%s, %s, %s)' % (i['file'], found, file_or_dir, item_path))
                if not found:
                    logger_ignore.warning('[Ignored]: item "%s" not found in "%s" (%s).' % (i['file'], dir.get_fullpath(), file_or_dir))
                else:
                    ignore_flag = self.read_ignore_information(i['ignore'], item_path)
                    ignore_info[item_path] = {
                        'name': item_name,
                        'ignore': ignore_flag,
                        'file_or_dir': file_or_dir
                    }
                    logger_ignore.debug(pp.pformat(ignore_info))
                    # util.WebifyLogger.get('ignored').info('[Ignored]: %s (%s)' % (item_path, ignore_flag))
        except:
            self.logger.warning('[Ignore]: cannot read ignore information: %s' % dir.get_fullpath())
            return ignore_info
        
        logger_ignore.debug('Ignore info:')
        logger_ignore.debug(pp.pformat(ignore_info))
        return ignore_info

    @staticmethod
    def read_ignore_information(x, filepath):
        if x == True or x == False:
            return x
        else:
            util.WebifyLogger.get('ignore').warning('Ignore value can only be true or false: %s' % filepath)
            return False

    def load_availability_info(self, dir):
        logger_availability = util.WebifyLogger.get('availability')
        logger_availability.debug('Loading availability info for folder %s' % dir.get_fullpath())

        availability = {}
        x = self.rc.value('availability')
        if not x:
            logger_availability.debug('No availability information found in folder %s' % dir.get_fullpath())
            return availability
        else:
            logger_availability.debug('Availability information found in folder %s' % dir.get_fullpath())
            logger_availability.debug(pp.pformat(x))

        try:
            if not isinstance(x, list):
                x = [x]
            for i in x:
                found, file_or_dir, item_path, item_name = self.check_item_in_cur_folder(dir, i['file'])
                logger_availability.debug('Availability: check %s: (%s,%s,%s)' % (i['file'], found, file_or_dir, item_path))
                if not found:
                    logger_availability.warning('[Availability]: item %s not found in this folder (%s).' % (i['file'], file_or_dir))
                else:
                    availability[item_path] = {
                        'name': item_name,
                        'start': tm.read_time('start', i),
                        'end': tm.read_time('end', i),
                        'file_or_dir': file_or_dir                     
                    }
                    logger_availability.debug(pp.pformat(availability))
        except:
            self.logger.warning('[Availability]: cannot read availability information: %s' % dir.get_fullpath())
            return availability

        logger_availability.debug('Availability:')
        logger_availability.debug(pp.pformat(availability))
        return availability

    def find_next_time_to_run(self, ts, te, filepath):
        logger = util.WebifyLogger.get('next-run')
        logger.debug('ESTIMATING next run time: %s' % filepath)

        tc = self.meta_data['__time__']
        next_time = tm.find_next_time(ts, te, tc)
        logger.debug('ts: %s, te: %s, next: %s' % (ts, te, next_time))
        
        if next_time != None:
            if self.next_run_time == None or self.next_run_time > next_time:
                self.next_run_time = next_time 

        logger.debug('Next time run time: %s' % self.next_run_time)

    def enter_dir(self, dir):
        self.depth_level = self.depth_level + 1
        self.logger.info('> [%d] entering folder %s' % (self.depth_level, dir.get_fullpath()))

        logger_rc =  util.WebifyLogger.get('rc')
        logger_rc.debug('Rendering context (before entering %s):' % dir.get_fullpath())
        logger_rc.debug(pp.pformat(self.rc.data()))

        self.rc.push()
        self.rc.add({'__root__': os.path.relpath(self.srcdir, dir.get_fullpath()).replace('\\','/')})
        self.rc.remove('availability')
        self.rc.remove('ignore')

        self.dir_stack.push(dir.name)

        logger_rc.debug('Rendering context (entering %s):' % dir.get_fullpath())
        logger_rc.debug(pp.pformat(self.rc.data()))

    def proc_dir(self, dir):
        self.proc_yaml(dir)
        self.proc_partials(dir)

        destdir = os.path.normpath(os.path.join(self.destdir, dir.path, dir.name))
        if os.path.isdir(destdir):
            self.logger.info('Destination directory exists: %s' % destdir)
        else:
            self.logger.info('Making destination directory: %s' % destdir)
            util.make_directory(destdir)

        # Collecting sub-directories that should be skipped
        # in the current directory
        skipped_sub_dirs = []

        # Handling directory ignore information
        ignore_info = self.load_ignore_info(dir)
        for (k,v) in ignore_info.items():
            if v['file_or_dir'] == 'dir' and v['ignore'] == True:
                skipped_sub_dirs.append(k)
                dest_path = self.make_output_filepath(dir, v['name'])
                status, message = util.remove_dir(dest_path)
                util.WebifyLogger.get('ignore').debug('Ignore: ignore info for directory %s: True.' % k) # --debug-ignore
                util.WebifyLogger.get('ignore').debug('Ignore: directory %s removed status: %s (%s)' % (dest_path, status, message) )
                if util.WebifyLogger.is_info(util.WebifyLogger.get('main')): # verbose
                    util.WebifyLogger.get('main').info('x-: %s' % k)
                    if status:
                        util.WebifyLogger.get('main').info('    %s removed' % dest_path)
                else:
                    util.WebifyLogger.get('ignored').info('Ignored:\n   skipped %s' % k ) # --show-ignore
                if not status:
                    util.WebifyLogger.get('ignored').warning('Ignored: Directory removal failed: %s' % dest_path)

        # Handing directory availability information
        availability = self.load_availability_info(dir)
        for (k,v) in availability.items():
            if v['file_or_dir'] == 'dir' and (not self.check_availability_(v['start'], v['end'], k)):
                skipped_sub_dirs.append(k)
                dest_path = self.make_output_filepath(dir, v['name'])
                status, message = util.remove_dir(dest_path)
                util.WebifyLogger.get('availability').debug('Availability: availability info for directory %s: True.' % k) # --debug-ignore
                util.WebifyLogger.get('availability').debug('Availability: directory %s removed status: %s (%s)' % (dest_path, status, message) )
                if util.WebifyLogger.is_info(util.WebifyLogger.get('main')): # verbose
                    util.WebifyLogger.get('main').info('x-: %s' % k)
                    if status:
                        util.WebifyLogger.get('main').info('    %s removed' % dest_path)
                else:
                    util.WebifyLogger.get('available').info('Availability:\n   sipped %s' % k ) # --show-availability
                if not status:
                    util.WebifyLogger.get('available').warning('Availability: Directory removal failed: %s' % dest_path)

        return skipped_sub_dirs, availability, ignore_info

    def leave_dir(self, dir, availability, ignore_info):
        self.logger.info('- [%d] back in folder %s' % (self.depth_level, dir.get_fullpath()))

        logger_dirlist = util.WebifyLogger.get('dirlist')
        logger_dirlist.info('Capturing file list from %s' % dir.get_fullpath())

        list_html = self.capture_list_of(dir, availability, ignore_info, 'html')
        list_md = self.capture_list_of_md(dir, availability, ignore_info)
        list_ipynb = self.capture_list_of_ipynb(dir, availability, ignore_info)
        list_misc = self.capture_list_of(dir, availability, ignore_info, 'misc')

        logger_dirlist.debug('--- local list starts --- (%s)' % dir.get_fullpath())
        logger_dirlist.debug(pp.pformat(list_html))
        logger_dirlist.debug(pp.pformat(list_md))
        logger_dirlist.debug(pp.pformat(list_ipynb))
        logger_dirlist.debug(pp.pformat(list_misc))
        logger_dirlist.debug('--- local list ends ---')

        self.dir_stack.top()[1].extend(list_html)
        self.dir_stack.top()[1].extend(list_md)
        self.dir_stack.top()[1].extend(list_ipynb)
        self.dir_stack.top()[1].extend(list_misc)

        logger_dirlist.debug('--- full list starts --- (%s)' % dir.get_fullpath())
        logger_dirlist.debug(pp.pformat(self.dir_stack.top()))
        logger_dirlist.debug('--- full list ends ---')

        self.rc.add({'__md__': list_md,
                     '__html__': list_html,
                     '__misc__': list_misc,
                     '__ipynb__': list_ipynb,
                     '__files__': self.dir_stack.top()[1]})

        logger_rc =  util.WebifyLogger.get('rc')
        logger_rc.debug('Rendering context (in %s):' % dir.get_fullpath())
        logger_rc.debug(pp.pformat(self.rc.data()))

        if len(list_misc) > 0 or len(list_md) > 0 or len(list_html) > 0 or len(list_ipynb) > 0:
            self.logger.info('Saving files to %s' % self.make_output_filepath(dir, ''))
            self.proc_files(dir, list_html)
            self.proc_files(dir, list_md)
            self.proc_files(dir, list_ipynb)
            self.proc_files(dir, list_misc)

        self.rc.remove(['__md__', '__html__', '__misc__', '__ipynb__', '__files__'])

        self.rc.pop()
        self.copy_dir_list_to_parent()

        logger_rc.debug('Rendering context (leaving %s):' % dir.get_fullpath())
        logger_rc.debug(pp.pformat(self.rc.data()))
        
        self.logger.info('< [%d] leaving folder %s' % (self.depth_level, dir.get_fullpath()))
        self.depth_level = self.depth_level - 1
        
    def copy_dir_list_to_parent(self):
        logger_dirlist = util.WebifyLogger.get('dirlist')
        logger_dirlist.debug('Copying dirlist to parent folder')

        x = self.dir_stack.top()
        logger_dirlist.debug(x[0])
        self.dir_stack.pop()
        y = self.dir_stack.top()
        for i in x[1]:
            i['filename'] = os.path.join(x[0], i['filename'])
            y[1].append(i)        

    def traverse(self):
        assert(self.srcdir and self.destdir and self.meta_data)

        tic = time.time()
        self.next_run_time = None
        self.depth_level = 0
        self.dir_tree.collect(rootdir=self.srcdir, ignore=self.ignore)
        self.dir_tree.traverse(enter_func=self.enter_dir, proc_func=self.proc_dir, leave_func=self.leave_dir)
        toc = time.time()
        logger.critical('Webify took {}'.format(datetime.timedelta(seconds=toc-tic)))
        util.WebifyLogger.get('next-run').debug('Next run time: %s' % self.next_run_time)

def version_info():
    return 'Webify version %s' % __version__

def select_loglevel(loglevel, cmdline_arg, default=logging.WARNING):
    if loglevel > default:
        loglevel = default
    
    if cmdline_arg:
        loglevel = logging.DEBUG

    return loglevel

def check_cmdline_args(is_live, cmdline_args):
    logger = util.WebifyLogger.get('main')
    
    if is_live:
        pass
    else:
        if cmdline_args.upload_script != None:
            logger.warning('Upload script is only supported in "--live" mode: %s' % cmdline_args.upload_script)

if __name__ == '__main__':
    # util.terminal = util.Terminal()
    prog_name = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
    prog_dir = os.path.dirname(prog_name)
    cur_dir = os.getcwd()

    # Command line arguments
    cmdline_parser = argparse.ArgumentParser()
    cmdline_parser.add_argument('srcdir', help='Source directory')
    cmdline_parser.add_argument('destdir', help='Destination directory')
    cmdline_parser.add_argument('-i', '--ignore-times', action='store_true', default=False, help='Forces the generation of the output file even if the source file has not changed')
    cmdline_parser.add_argument('--force-copy', action='store_true', default=False, help='Force file copy.')    

    cmdline_parser.add_argument('--version', action='version', version=version_info())
    cmdline_parser.add_argument('-v','--verbose',action='store_true',default=False,help='Prints helpful messages')
    cmdline_parser.add_argument('-d','--debug',action='store_true',default=False,help='Turns on (global) debug messages')
    cmdline_parser.add_argument('-l','--log', action='store_true', default=False, help='Use log file.')

    cmdline_parser.add_argument('--debug-rc',action='store_true',default=False,help='Turns on rendering context debug messages')
    cmdline_parser.add_argument('--debug-dirlist',action='store_true',default=False,help='Turns on blogging debug messages')
    cmdline_parser.add_argument('--debug-db',action='store_true',default=False,help='Turns on file database debug messages')
    cmdline_parser.add_argument('--debug-db-ignore',action='store_true',default=False,help='Turns on .webifyignore debug messages')
    cmdline_parser.add_argument('--debug-yaml',action='store_true',default=False,help='Turns on yaml debug messages')
    cmdline_parser.add_argument('--debug-render',action='store_true',default=False,help='Turns on render debug messages')
    cmdline_parser.add_argument('--debug-md',action='store_true',default=False,help='Turns on mdfile debug messages')
    cmdline_parser.add_argument('--debug-html',action='store_true',default=False,help='Turns on html debug messages')
    cmdline_parser.add_argument('--debug-availability',action='store_true',default=False,help='Turns on availability debug messages')
    cmdline_parser.add_argument('--debug-ignore',action='store_true',default=False,help='Turns on ignore debug messages')
    cmdline_parser.add_argument('--debug-live',action='store_true',default=False,help='Turns on live run debug messages')
    cmdline_parser.add_argument('--debug-next-run',action='store_true',default=False,help='Turns on next run debug messages')
    cmdline_parser.add_argument('--debug-nb',action='store_true',default=False,help='Turns on Jupyter Notebooks debug messages')
    cmdline_parser.add_argument('--debug-nb-settings',action='store_true',default=False,help='Turns on Jupyter Notebooks Settings debug messages')

    cmdline_parser.add_argument('--show-availability',action='store_true',default=False,help='Turns on messages that are displayed if a file is ignored due to availability')
    cmdline_parser.add_argument('--show-not-compiled',action='store_true',default=False,help='Turns on messages that are displayed if a file is not compiled because it already exists')
    cmdline_parser.add_argument('--show-not-copied',action='store_true',default=False,help='Turns on messages that are displayed if a file is not copied because it already exists at the destination')
    cmdline_parser.add_argument('--show-compiled',action='store_true',default=False,help='Turns on messages that are displayed if a file is compiled')
    cmdline_parser.add_argument('--show-ignored',action='store_true',default=False,help='Turns on messages that are displayed if a file is ignored')
    
    cmdline_parser.add_argument('--live',action='store_true',default=False,help='Monitors changes in the root folder and invokes source-to-web compilation as needed')
    cmdline_parser.add_argument('--upload-script',action='store',default=None,help='Specifies the shell script that copies the compiled website to the hosting server')
    cmdline_parser.add_argument('--live-url-prefix',action='store',default=None,help='Specify url prefix for --live mode')

    cmdline_parser.add_argument('--renderer', action='store', default=None, help='Specify whether to use mustache or jinja2 engine.  Jinja2 is the default choice.')
    
    cmdline_parser.add_argument('--pandoc-var', action='append', default=[], help='A mechanism for providing -V Name:Val for pandoc.')
    cmdline_parser.add_argument('--pandoc-meta', action='append', default=[], help='A mechanism for providing -M Name:Val for pandoc.')

    cmdline_parser.add_argument('--execute-jupyter-notebook', action='store_true',default=False,help='Executes jupyter notebook(s) before converting these to html.  This can take a long time, depending upon the contents of the jupyter notebooks.')


    cmdline_args = cmdline_parser.parse_args()
    
    # Setting up logging
    logfile = None if not cmdline_args.log else logfile
    loglevel = logging.INFO  if cmdline_args.verbose else logging.WARNING
    loglevel = logging.DEBUG if cmdline_args.debug else loglevel
    
    util.WebifyLogger.make(name='main', loglevel=loglevel, logfile=logfile)

    util.WebifyLogger.make(name='html', loglevel=logging.DEBUG if cmdline_args.debug_html else loglevel, logfile=logfile)    
    util.WebifyLogger.make(name='rc', loglevel=logging.DEBUG if cmdline_args.debug_rc else loglevel, logfile=logfile)    
    util.WebifyLogger.make(name='db', loglevel=logging.DEBUG if cmdline_args.debug_db else loglevel, logfile=logfile)    
    util.WebifyLogger.make(name='yaml', loglevel=logging.DEBUG if cmdline_args.debug_yaml else loglevel, logfile=logfile)    
    util.WebifyLogger.make(name='render', loglevel=logging.DEBUG if cmdline_args.debug_render else loglevel, logfile=logfile)    
    util.WebifyLogger.make(name='db-ignore', loglevel=logging.DEBUG if cmdline_args.debug_db_ignore else loglevel, logfile=logfile)    
    util.WebifyLogger.make(name='dirlist', loglevel=logging.DEBUG if cmdline_args.debug_dirlist else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='availability', loglevel=logging.DEBUG if cmdline_args.debug_availability else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='ignore', loglevel=logging.DEBUG if cmdline_args.debug_ignore else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='next-run', loglevel=logging.DEBUG if cmdline_args.debug_next_run else loglevel, logfile=logfile)

    util.WebifyLogger.make(name='available', loglevel=logging.INFO if cmdline_args.show_availability else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='not-compiled', loglevel=logging.INFO if cmdline_args.show_not_compiled else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='compiled', loglevel=logging.INFO if cmdline_args.show_compiled else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='ignored', loglevel=logging.INFO if cmdline_args.show_ignored else loglevel, logfile=logfile)

    util.WebifyLogger.make(name='not-copied', loglevel=logging.INFO if cmdline_args.show_not_copied else loglevel, logfile=logfile)

    util.WebifyLogger.make(name='md-file', loglevel=logging.ERROR if not cmdline_args.debug_md else logging.DEBUG, logfile=logfile)
    util.WebifyLogger.make(name='md-buffer', loglevel=logging.ERROR, logfile=logfile)
    util.WebifyLogger.make(name='md-rc', loglevel=logging.ERROR, logfile=logfile)
    util.WebifyLogger.make(name='md-timestamps', loglevel=logging.ERROR, logfile=logfile)

    util.WebifyLogger.make(name='nb', loglevel=select_loglevel(loglevel, cmdline_args.debug_nb), logfile=logfile)
    util.WebifyLogger.make(name='nb-settings', loglevel=select_loglevel(loglevel, cmdline_args.debug_nb_settings), logfile=logfile)


    logger = util.WebifyLogger.get('main')

    # Check
    if not cmdline_args.renderer in [None, 'mustache', 'jinja2']:
        logger.error('Invalid templating engine %s.  See help' % cmdline_args.templateqing_engine)
        exit(-4)

    # Go        
    logger.info('Prog name:    %s' % prog_name)
    logger.info('Prog dir:     %s' % prog_dir)
    logger.info('Current dir:  %s' % cur_dir)
    logger.info('Info:')
    logger.info(version_info())
    logger.info('Renderer:     %s' % cmdline_args.renderer)
    
    srcdir = os.path.normpath(cmdline_args.srcdir)
    destdir = os.path.normpath(cmdline_args.destdir)
    
    cur_time = datetime.datetime.now()
    meta_data = {
        'prog_name': prog_name.replace('\\','/'),
        'prog_dir': prog_dir.replace('\\','/'), # We need to do it for windows.
        'cur_dir': cur_dir.replace('\\','/'),   # It is a bit wierd, I agree.
        'src_dir': srcdir.replace('\\','/'),    # But it seems mustache templating engine
        'dest_dir': destdir.replace('\\','/'),  # can't deal with \.  Will look into it more.
        '__version__': __version__,
        '__root__': os.path.abspath(cmdline_args.srcdir).replace('\\','/'),
        '__last_updated__': cur_time.strftime('%Y-%m-%d %H:%M'),
        'renderer': cmdline_args.renderer,
        '__force_copy__': cmdline_args.force_copy,
        '__time__': cur_time,
        '__ignore_times__': cmdline_args.ignore_times,
        'pandoc-var': cmdline_args.pandoc_var,
        'pandoc-meta': cmdline_args.pandoc_meta,
        'execute_jupyter-notebook': cmdline_args.execute_jupyter_notebook
    }
    logger.debug('Meta data:')
    logger.debug(pp.pformat(meta_data))

    webify = Webify()
    try:
        webify.set_src(srcdir)
        webify.set_meta_data(meta_data)
    except ValueError as e:
        print(e)
        exit(-1)
    try:           
        webify.set_dest(destdir)
    except ValueError as e:
        print(e)
        exit(-2)
    
    check_cmdline_args(is_live=cmdline_args.live, cmdline_args=cmdline_args)

    if not cmdline_args.live:
        webify.traverse()
        if webify.next_run_time != None:
            logger.critical('Next suggested run at {}'.format(webify.next_run_time))
    else:
        import running as run

        loglevel == logging.INFO
        # util.WebifyLogger.make(name='webify-live', loglevel=logging.DEBUG if cmdline_args.debug_live else loglevel, logfile=logfile)
        util.WebifyLogger.make(name='watchdir', loglevel=logging.DEBUG if cmdline_args.debug_live else loglevel, logfile=logfile)
        util.WebifyLogger.make(name='keyboard', loglevel=logging.DEBUG if cmdline_args.debug_live else loglevel, logfile=logfile)
        util.WebifyLogger.make(name='browser', loglevel=logging.DEBUG if cmdline_args.debug_live else loglevel, logfile=logfile)
        util.WebifyLogger.make(name='upload', loglevel=logging.DEBUG if cmdline_args.debug_live else loglevel, logfile=logfile)
        util.WebifyLogger.make(name='run-webify', loglevel=logging.DEBUG if cmdline_args.debug_live else logging.INFO, logfile=logfile)

        logger.critical('Webifying folder "%s" into "%s"' % (srcdir, destdir))

        upload_script = None if cmdline_args.upload_script == None else os.path.join(cur_dir, cmdline_args.upload_script)
        if upload_script:
            if not os.path.isfile(upload_script):
                util.WebifyLogger.get('upload').warning('Cannot find upload script: %s' % upload_script)
                upload_script = None
            else:
                logger.critical('Using uploader script: %s' % upload_script)
        else:
            logger.info('Not using an uploader script')

        logger.critical('Press h to see the list of available commands.')
        logger.critical('Press q to exit.')

        run.WebifyLive(webify=webify, url_prefix=cmdline_args.live_url_prefix, upload_shell_script=upload_script)
