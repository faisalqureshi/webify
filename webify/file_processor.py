from util2 import copy_file, WebifyLogger
import os

def CopyFile(filepath, dest_filepath, force_copy):
    logger = WebifyLogger.get('webify')

    r = copy_file(filepath, dest_filepath, force_copy)
    if r == 'Failed':
        logger.warning('%s: %s' % (r, dest_filepath))
    else:
        logger.info('%s: %s' % (r, dest_filepath))

def JupyterNotebook(filepath, dest_filepath, force_save):
    logger = WebifyLogger.get('webify')

    f, _ = os.path.splitext(dest_filepath)
    f += '.html'
    try:
        from nbconvert.exporters import HTMLExporter
        exporter = HTMLExporter()
        output, resources = exporter.from_filename(filepath)
        logger.debug('Jupyter notebook conversion succeeded: %s' % f)

        dest_filename = os.path.basename(dest_filepath)
        s = '\n<body>\n<span style="font-size:x-large;">HTML generated from Jupyter notebook: <a href="%s">%s</a></span>\n' % (dest_filename, dest_filename)
        output = output.replace('<body>', s, 1)
        open(f, mode='w', encoding='utf-8').write(output)
    except:
        logger.warning('Jupyter notebook conversion failed: %s' % f)
        
    r = copy_file(filepath, dest_filepath, force_save)        
    if r == 'Failed':
        logger.warning('%s: %s' % (r, dest_filepath))
    else:
        logger.info('%s: %s' % (r, dest_filepath))
