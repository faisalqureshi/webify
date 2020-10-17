import util2 as util
import os


def JupyterNotebook(filepath, dest_filepath, force_save):
    logger = util.WebifyLogger.get('webify')

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
        
    return util.copy_file(filepath, dest_filepath, force_save)

def JupyterNotebookOnlyHTML(filepath, dest_filepath, force_save):
    logger = util.WebifyLogger.get('webify')

    f, _ = os.path.splitext(dest_filepath)
    f += '.html'
    try:
        from nbconvert.exporters import HTMLExporter
        exporter = HTMLExporter()
        output, resources = exporter.from_filename(filepath)
        open(f, mode='w', encoding='utf-8').write(output)
        logger.debug('Jupyter notebook conversion succeeded: %s' % f)
    except:
        logger.warning('Jupyter notebook conversion failed: %s' % f)
        return Failed, 'Copy Failed'

    return True, 'Copied'
