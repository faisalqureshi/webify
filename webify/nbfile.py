import util2 as util
import os

def JupyterNotebookToHTML(filename, filepath, dest_filepath):
    logger = util.WebifyLogger.get('webify')

    try:
        from nbconvert.exporters import HTMLExporter
        exporter = HTMLExporter()
        output, resources = exporter.from_filename(filepath)
        open(dest_filepath, mode='w', encoding='utf-8').write(output)
        if util.WebifyLogger.is_info(logger):
            logger.info('    Compiled.')
        else:
            util.WebifyLogger.get('compiled').info('Compiled %s to %s' % (filename, dest_filepath))
        logger.info('    Saved')
    except:
        logger.warning('Jupyter notebook conversion failed: %s' % dest_filepath)
        return Failed, 'Copy Failed'

    return True, 'Copied'
