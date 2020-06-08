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
import w
import dirtree as dt
import dirstack as ds
from yamlfile import YAMLfile
from htmlfile import HTMLfile

from globals import __version__
logfile = 'webify2.log'
ignorefile = '.webifyignore'
ignore_times = False

class Webify:
    def __init__(self):
        self.logger = util.WebifyLogger.get('main')
        self.rc = RenderingContext.RenderingContext()
        self.ignore = None
        self.dir_tree = dt.DirTree()
        self.dir_stack = ds.DirStack()

    def set_renderer(self):
        if self.meta_data['renderer'] in [None, 'jinja2']:
            self.render = util.jinja2_renderer
        else:
            self.render = util.mustache_renderer
        
    def set_src(self, srcdir, meta_data):
        self.meta_data = meta_data
        self.srcdir = os.path.abspath(srcdir)
        if not os.path.isdir(self.srcdir):
            self.logger.critical('Source folder not found: %s' % srcdir)
            self.logger.critical('Nothing to do here.')
            raise ValueError('Error source folder')
        else:
            self.logger.info('Source folder found: %s' % srcdir)
            self.ignore = util.IgnoreList(srcdir=self.srcdir)
            self.ignore.read_ignore_file(os.path.abspath(os.path.join(srcdir, ignorefile)))

        self.set_renderer()            
        self.rc.push()
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

    def check_availability(self, filepath, availability):
        try:
            s = availability[filepath]['start']
            e = availability[filepath]['end']
            v = tm.check_for_time_in_range(s, e, self.meta_data['__time__'])
            if v == 'error':
                self.logger('Error reading availability times for %s' % filepath)
                return False
            return v
        except:
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
                rendered_buf = self.render(template=buffer, context=self.rc.data(), file_info=filepath)
                data[filename.replace('.','_')] = markupsafe.Markup(rendered_buf)

            # Load Markdown
            if len(dir.partials.files['md']) > 0:
                self.logger.info('Processing  MD files ...')
            else:
                self.logger.info('No MD files found')
            args = { 'create-output-file': False, 
                     'ignore-times': ignore_times }
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
    
    def capture_list_of(self, dir, availability, file_type):
        list_files = []
        for filename in dir.files[file_type]:
            filepath = self.make_src_filepath(dir, filename)
            output_filepath = self.make_output_filepath(dir, filename)
            is_available = self.check_availability(filepath, availability)
            self.capture_dir_listing_information(list_files, filename, filename, is_available, filepath, output_filepath, file_type, obj=None, data=None)
        return list_files

    def capture_list_of_md(self, dir, availability):
        list_files = []
        for filename in dir.files['md']:
            filepath = self.make_src_filepath(dir, filename)
            output_filepath = self.make_output_filepath(dir, filename)
            is_available = self.check_availability(filepath, availability)

            self.rc.push()
            
            args = { 'ignore-times': ignore_times,
                     'output-filepath': os.path.splitext(output_filepath)[0],
                     'output-fileext': '' }
            md_file = MDfile(filepath=filepath, args=args)
            md_file = self.md_set_defaults(md_file)
            loaded_ok = md_file.load(self.rc)
            if loaded_ok:
                converted_output_filepath = md_file.make_output_filepath()
                converted_filename = os.path.split(converted_output_filepath)[1]
                should_process, _, _, _ = self.md_inspect_frontmatter(md_file)
            else:
                converted_output_filepath = output_filepath
                converted_filename = filename

            if is_available and loaded_ok and should_process:
                if md_file.get_value('copy-source'):
                    self.capture_dir_listing_information(list_files, filename, filename, True, filepath, output_filepath, 'md-src', obj=None, data=None)

                self.capture_dir_listing_information(list_files, filename, converted_filename, True, filepath,converted_output_filepath, 'md', obj=md_file, data=md_file.get_yaml())
            else:
                self.capture_dir_listing_information(list_files, filename, converted_filename, False, filepath, converted_output_filepath, 'md', obj=None, data=None)

            self.rc.pop()
        return list_files

    def proc_files(self, dir, dir_list):

        for i in dir_list:
            src_filename = i['src_filename']
            filename = i['filename']
            filepath = i['filepath']
            is_available = i['is_available']
            output_filepath = i['output_filepath']
            file_type = i['file_type']

            if not is_available:
                if util.WebifyLogger.is_info(self.logger):
                    self.logger.info('x: %s' % filename) 
                else:
                    util.WebifyLogger.get('available').info('Skipped due to availability %s' % filepath)
                x, m = util.remove_file(output_filepath)
                if x:
                    self.logger.info('   Removed %s' % output_filepath)
                else:
                    util.WebifyLogger.get('available').warning('%s: (%s)' % (m, output_filepath))
                continue

            self.logger.info('x: %s -> %s' % (src_filename, filename))
            if file_type == 'html':
                self.convert_html(filename, filepath, output_filepath)
            elif file_type == 'misc':
                self.copy_misc(filename, filepath, output_filepath)
            elif file_type == 'md-src':
                self.copy_misc(filename, filepath, output_filepath)
            elif file_type == 'md':
                self.convert_md(filename, filepath, output_filepath, i['obj'])
                i['obj'] = None
            else:
                pass
            


    # def proc_html(self, dir, availability):
    #     if len(dir.files['html']) > 0:
    #         self.logger.info('Processing  HTML files...')
    #     else:
    #         self.logger.info('No HTML files found')
                
    #     for filename in dir.files['html']:
    #         filepath = self.make_src_filepath(dir, filename)
    #         output_filepath = self.make_output_filepath(dir, filename)
    #         if self.check_availability(filepath, availability):
    #             self.html_convert(filename, filepath, output_filepath)
    #         else:
    #             util.WebifyLogger.get('available').info('Skipped due to availability %s' % filepath)
    #             util.remove_file(output_filepath)

    def convert_html(self, filename, filepath, output_filepath):
        html_file = HTMLfile(filepath)
        buffer = html_file.load().get_buffer()
        rendered_buf = self.render(template=buffer, context=self.rc.data(), file_info=filepath)
        if util.save_to_file(output_filepath, rendered_buf):
            self.logger.info('   Saved')
        else:
            self.logger.warning('Error saving html file %s' % output_filepath)

    def md_set_defaults(self, md_file):
        if self.meta_data['renderer']:
            md_file.set_default('renderer', self.meta_data['renderer'])
        return md_file    

    def md_inspect_frontmatter(self, md_file):
        filepath = md_file.get_filepath()
        output_filepath = md_file.make_output_filepath()

        if md_file.get_value('ignore'):
            return False, 'ignore', filepath, output_filepath

        if not md_file.get_availability(meta_data['__time__']):
            return False, 'not available', filepath, output_filepath

        return True, None, None, None

    def convert_md(self, filename, filepath,  output_filepath, md_file_obj):
        self.rc.push()

        status, saved_file, _ = md_file_obj.convert(self.rc)
        if status == 'file':
            if util.WebifyLogger.is_info(self.logger):
                self.logger.info('   Compiled.')
            else:
                util.WebifyLogger.get('compiled').info('Compiled %s to %s' % (md_file_obj.get_filename(), saved_file))
        elif status == 'exists':
            if util.WebifyLogger.is_info(self.logger):
                util.WebifyLogger.get('not-compiled').info('   Destination file already exists.  Did not compile.')
            else:
                util.WebifyLogger.get('not-compiled').info('Destination file already exists.  Did not compile.  (%s)' % filepath)
        else:
            saved_file = None
            self.logger.warning('Error processing %s' % filepath)
        
        self.rc.pop()
                    
        #     if saved_file:
        #         copy_source = md_file.get_value('copy-source')
        #         if copy_source:
        #             self.logger.debug('Copying %s' % args['output-filepath']+'.md')
        #             util.process_file(filepath, args['output-filepath']+'.md', self.meta_data['force_copy'])

        #         # self.capture_dir_listing_information(filepath, saved_file, md_file.get_yaml())
        # else:
        #     if message == 'ignore':
        #         util.WebifyLogger.get('ignored').info('Ignored %s' % filepath)
        #     elif message == 'not available':
        #         util.WebifyLogger.get('available').info('Skipped due to availability %s' % filepath)
        #     else:
        #         pass
        #     util.remove_file(dest)
            
        # self.rc.pop()

    # def proc_md(self, dir, availability):
    #     if len(dir.files['md']) > 0:
    #         self.logger.info('Processing MD files...')
    #     else:
    #         self.logger.info('No MD files found')

    #     for filename in dir.files['md']:
    #         filepath = self.make_src_filepath(dir, filename)
    #         output_filepath = self.make_output_filepath(dir, filename)
    #         if self.check_availability(filepath, availability):
    #             self.md_convert(filename, filepath, output_filepath)
    #         else:
    #             util.WebifyLogger.get('available').info('Skipped due to availability %s' % filepath)
    #             util.remove_file(output_filepath)

    def capture_dir_listing_information(self, list_files, filename, converted_filename, is_available, filepath, output_filepath, file_type, obj, data):
        entry = {
            'src_filename': filename,
            'filename': converted_filename,
            'is_available': is_available,
            'filepath': filepath,
            'output_filepath': output_filepath,
            'file_type': file_type,
            'obj': obj,
            'data': data
        }
        self.logger.info('%s: %s' % ('+' if is_available else '-', filename))
        list_files.append(entry)

    def make_src_filepath(self, dir, filename):
        filepath =  os.path.join(dir.get_fullpath(), filename)
        return os.path.normpath(filepath)

    def make_output_filepath(self, dir, filename):
        output_filepath = os.path.join(self.destdir, dir.path, dir.name, filename)
        return os.path.normpath(output_filepath)
                
    def copy_misc(self, filename, filepath, output_filepath):
        v, s = util.process_file(filepath, output_filepath, self.meta_data['force_copy'])
        if not v:
            logger.warning('%s (%s)' % (filepath, s))
        else:
            if s == 'Exists':
                if util.WebifyLogger.is_info(self.logger):
                    util.WebifyLogger.get('not-copied').info('   Destination file already exists.  Did not copy.')
                else:
                    util.WebifyLogger.get('not-copied').info('Did not copy.  Destination file already exists.  (%s)' % filepath)        

    # def proc_misc(self, dir, availability):
    #     if len(dir.files['misc']) > 0:
    #         self.logger.info('Processing all other files...')
    #     else:
    #         self.logger.info('No other files found')

    #     for filename in dir.files['misc']:
    #         filepath = self.make_src_filepath(dir, filename)
    #         output_filepath = self.make_output_filepath(dir, filename)
    #         if self.check_availability(filepath, availability):
    #             self.logger.info('Processing %s' % filepath)
    #             v, s = util.process_file(filepath, output_filepath, self.meta_data['force_copy'])
    #             if not v:
    #                 logger.warning('%s (%s)' % (filepath, s))
    #             else:
    #                 if s == 'Exists':
    #                     util.WebifyLogger.get('not-copied').info('Already exists (did not copy) %s' % filepath)
    #         else:
    #             util.WebifyLogger.get('available').info('Skipped due to availability %s' % filepath)
    #             v, s = util.remove_file(output_filepath)
    #             if not v:
    #                 logger.warning('%s (%s)' % (filepath, s))

    def check_file_in_folder(self, dir, filename):
        cur_dir = dir.get_fullpath()
        filepath = self.make_src_filepath(dir, os.path.expandvars(filename))
        file_dir = os.path.split(filepath)[0]
        if file_dir != cur_dir:
            return False, 'Not in directory'
        elif not os.path.isfile(filepath):
            return False, 'Not a file'
        else:
            return True, filepath 

    def load_availability_info(self, dir):
        availability = {}
        x = self.rc.value('availability')
        if not x:
            return availability

        try:
            if not isinstance(x, list):
                x = [x]
            for i in x:
                v, s = self.check_file_in_folder(dir, i['file'])
                if not v:
                    self.logger.warning('Cannot read availability information for %s (%s)' % (i['file'], s))
                else:
                    availability[v] = {}
                    availability[v]['start'] = i['start'] if 'start' in i.keys() else 'big-bang'
                    availability[v]['end'] = i['end'] if 'end' in i.keys() else 'ragnarok'
        except:
            self.logger.warning('Cannot read availability information: %s' % dir.get_fullpath())
            return availability

        return availability

    def enter_dir(self, dir):
        self.depth_level = self.depth_level + 1
        self.logger.info('> [%d] entering folder %s' % (self.depth_level, dir.get_fullpath()))

        logger_rc =  util.WebifyLogger.get('rc')
        logger_rc.debug('Rendering context:')
        logger_rc.debug(pp.pformat(self.rc.data()))

        self.rc.push()
        self.rc.add({'__root__': os.path.relpath(self.srcdir, dir.get_fullpath())})
        self.rc.remove('availability')
        self.dir_stack.push(dir.name)

    def proc_dir(self, dir):
        self.proc_yaml(dir)
        self.proc_partials(dir)

        logger_rc =  util.WebifyLogger.get('rc')
        logger_rc.debug('Rendering context (%s):' % dir.get_fullpath())
        logger_rc.debug(pp.pformat(self.rc.data()))

        destdir = os.path.normpath(os.path.join(self.destdir, dir.path, dir.name))
        if os.path.isdir(destdir):
            self.logger.info('Destination directory exists: %s' % destdir)
        else:
            self.logger.info('Making destination directory: %s' % destdir)
            util.make_directory(destdir)

    def leave_dir(self, dir):
        self.logger.info('- [%d] back in folder %s' % (self.depth_level, dir.get_fullpath()))

        availability = self.load_availability_info(dir)

        dirlist_logger = util.WebifyLogger.get('dirlist')

        dirlist_logger.info('Capturing file list from %s' % dir.get_fullpath())
        list_html = self.capture_list_of(dir, availability, 'html')
        list_md = self.capture_list_of_md(dir, availability)
        list_misc = self.capture_list_of(dir, availability, 'misc')
        dirlist_logger.debug(pp.pformat(self.dir_stack.top()))

        if len(list_misc) > 0 or len(list_md) > 0 or len(list_html) > 0:
            self.logger.info('Saving files to %s' % self.make_output_filepath(dir, ''))
            self.proc_files(dir, list_html)
            self.proc_files(dir, list_md)
            self.proc_files(dir, list_misc)

        self.dir_stack.top()[1].extend(list_html)
        self.dir_stack.top()[1].extend(list_md)
        self.dir_stack.top()[1].extend(list_misc)

        # self.proc_html(dir, availability)
        # self.proc_md(dir, availability)
        # self.proc_misc(dir, availability)
        self.rc.pop()
        self.copy_dir_list_to_parent()

        logger_rc =  util.WebifyLogger.get('rc')
        logger_rc.debug('Rendering context:')
        logger_rc.debug(pp.pformat(self.rc.data()))
        
        self.logger.info('< [%d] leaving folder %s' % (self.depth_level, dir.get_fullpath()))
        self.depth_level = self.depth_level - 1
        
    def copy_dir_list_to_parent(self):
        x = self.dir_stack.top()
        self.dir_stack.pop()
        y = self.dir_stack.top()
        for i in x[1]:
            i['filepath'] = os.path.join(x[0], i['filepath'])
            y[1].append(i)        

    def traverse(self):
        self.depth_level = 0
        self.dir_tree.collect(rootdir=self.srcdir, ignore=self.ignore)
        self.dir_tree.traverse(enter_func=self.enter_dir, proc_func=self.proc_dir, leave_func=self.leave_dir)

# def version_info():
#     str =  '  Webify2:    %s,\n' % __version__
#     str += '  logfile:    %s,\n' % logfile 
#     str += '  ignorefile: %s,\n' % ignorefile
#     str += '  Git info:   %s,\n' % util.get_gitinfo()
#     str += '  Python:     %s.%s,\n' % (sys.version_info[0],sys.version_info[1])
#     str += '  Pypandoc:   %s,\n' % pypandoc.__version__
#     str += '  Pyyaml:     %s,\n' % yaml.__version__
#     str += '  Pystache:   %s,\n' % pystache.__version__
#     str += '  Json:       %s, and\n' % json.__version__
#     str += '  Pathspec:   %s.' % pathspec.__version__
#     return str

def version_info():
    return 'Webify version %s' % __version__

if __name__ == '__main__':

    util.terminal = util.Terminal()
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

    cmdline_parser.add_argument('--show-availability',action='store_true',default=False,help='Turns on messages that are displayed if a file is ignored due to availability')
    cmdline_parser.add_argument('--show-not-compiled',action='store_true',default=False,help='Turns on messages that are displayed if a file is not compiled because it already exists')
    cmdline_parser.add_argument('--show-not-copied',action='store_true',default=False,help='Turns on messages that are displayed if a file is not copied because it already exists at the destination')
    cmdline_parser.add_argument('--show-compiled',action='store_true',default=False,help='Turns on messages that are displayed if a file is compiled')
    cmdline_parser.add_argument('--show-ignored',action='store_true',default=False,help='Turns on messages that are displayed if a file is ignored')
    
    cmdline_parser.add_argument('--live',action='store_true',default=False,help='Monitors changes in the root folder and invokes an autocompile')


    cmdline_parser.add_argument('--renderer', action='store', default=None, help='Specify whether to use mustache or jinja2 engine.  Jinja2 is the default choice.')
    
    cmdline_args = cmdline_parser.parse_args()
    ignore_times = cmdline_args.ignore_times
    
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
    util.WebifyLogger.make(name='db_ignore', loglevel=logging.DEBUG if cmdline_args.debug_db_ignore else loglevel, logfile=logfile)    
    util.WebifyLogger.make(name='dirlist', loglevel=logging.DEBUG if cmdline_args.debug_dirlist else loglevel, logfile=logfile)    



    # l = logging.DEBUG if cmdline_args.debug_rc else loglevel
    # util.WebifyLogger.make(name='rc', loglevel=l, logfile=logfile)

    # l = logging.DEBUG if cmdline_args.debug_db else loglevel
    # util.WebifyLogger.make(name='db', loglevel=l, logfile=logfile)

    # l = logging.DEBUG if cmdline_args.debug_yaml else loglevel    
    # util.WebifyLogger.make(name='yaml', loglevel=l, logfile=logfile)

    # l = logging.DEBUG if cmdline_args.debug_render else logging.WARNING    
    # util.WebifyLogger.make(name='render', loglevel=l, logfile=logfile)

    # # l = logging.DEBUG if cmdline_args.debug_md else logging.WARNING  
    # # util.WebifyLogger.make(name='md-file', loglevel=l, logfile=logfile)

    # l = logging.DEBUG if cmdline_args.debug_db_ignore else loglevel
    # util.WebifyLogger.make(name='db-ignore', loglevel=l, logfile=logfile)

    # l = logging.DEBUG if cmdline_args.debug_webify else loglevel
    # util.WebifyLogger.make(name='main', loglevel=l, logfile=logfile)


    util.WebifyLogger.make(name='available', loglevel=logging.INFO if cmdline_args.show_availability else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='not-compiled', loglevel=logging.INFO if cmdline_args.show_not_compiled else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='compiled', loglevel=logging.INFO if cmdline_args.show_compiled else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='ignored', loglevel=logging.INFO if cmdline_args.show_ignored else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='not-copied', loglevel=logging.INFO if cmdline_args.show_not_copied else loglevel, logfile=logfile)

    util.WebifyLogger.make(name='md-file', loglevel=logging.ERROR, logfile=logfile)
    util.WebifyLogger.make(name='md-buffer', loglevel=logging.ERROR, logfile=logfile)
    util.WebifyLogger.make(name='md-rc', loglevel=logging.ERROR, logfile=logfile)
    util.WebifyLogger.make(name='md-timestamps', loglevel=logging.ERROR, logfile=logfile)

    logger = util.WebifyLogger.get('webify')

    # Check
    if not cmdline_args.renderer in [None, 'mustache', 'jinja2']:
        logger.error('Invalid templating engine %s.  See help' % cmdline_args.templateing_engine)
        exit(-4)
        
    # Go        
    logger.info('Prog name:    %s' % prog_name)
    logger.info('Prog dir:     %s' % prog_dir)
    logger.info('Current dir:  %s' % cur_dir)
    logger.info('Info:')
    logger.info(version_info())
    logger.info('Renderer: %s   ' % cmdline_args.renderer)

    srcdir = os.path.normpath(cmdline_args.srcdir)
    destdir = os.path.normpath(cmdline_args.destdir)
    
    cur_time = datetime.datetime.now()

    meta_data = {
        'prog_name': prog_name,
        'prog_dir': prog_dir.replace('\\','\\\\'), # We need to do it for windows.
        'cur_dir': cur_dir.replace('\\','\\\\'),   # It is a bit wierd, I agree.
        'src_dir': srcdir.replace('\\','\\\\'),    # But it seems mustache templating engine
        'dest_dir': destdir.replace('\\','\\\\'),  # can't deal with \.  Will look into it more.
        '__version__': __version__,
        '__root__': os.path.abspath(cmdline_args.srcdir).replace('\\','\\\\'),
        '__last_updated__': cur_time.strftime('%Y-%m-%d %H:%M'),
        'renderer': cmdline_args.renderer,
        'force_copy': cmdline_args.force_copy,
        '__time__': cur_time
    }
    
    if util.WebifyLogger.is_debug(logger):
        print('Meta data:')
        pp.pprint(meta_data)

    webify = Webify()
    try:
        webify.set_src(srcdir, meta_data)
    except ValueError as e:
        print(e)
        exit(-1)
    try:           
        webify.set_dest(destdir)
    except ValueError as e:
        print(e)
        exit(-2)
    
    if not cmdline_args.live:
        webify.traverse()
    else:
        print('Webifying folder "%s" into "%s"' % (srcdir, destdir))
        print('Press ctrl-C to exit.')
        
        webify.traverse()
        w.start(w.RunWebify(webify), os.path.join(cur_dir, srcdir))
