import os
import re
import tempfile
from bika.lims.utils import to_utf8, encode_header
from email.MIMEBase import MIMEBase
from pkg_resources import resource_filename
from weasyprint import HTML, CSS
from zope.component.hooks import getSite

def attachCSV(mimemultipart,csvdata,filename):
    part = MIMEBase('text', "csv")
    part.add_header(
        'Content-Disposition', 'attachment; filename="{}.csv"'.format(filename))
    part.set_payload(csvdata)
    mimemultipart.attach(part)

def createPdf(htmlreport, outfile=None, css=None, images={}):
    """create a PDF from some HTML.
    htmlreport: rendered html
    outfile: pdf filename; if supplied, caller is responsible for creating
             and removing it.
    css: remote URL of css file to download
    images: A dictionary containing possible URLs (keys) and local filenames
            (values) with which they may to be replaced during rendering.
    # WeasyPrint will attempt to retrieve images directly from the URL
    # referenced in the HTML report, which may refer back to a single-threaded
    # (and currently occupied) zeoclient, hanging it.  All image source
    # URL's referenced in htmlreport should be local files.
    """
    # A list of files that should be removed after PDF is written
    htmlreport = to_utf8(htmlreport)
    cleanup, htmlreport = localize_images(htmlreport)
    css_def = ''
    if css:
        if css.startswith("http://") or css.startswith("https://"):
            # Download css file in temp dir
            u = urllib2.urlopen(css)
            _cssfile = tempfile.mktemp(suffix='.css')
            localFile = open(_cssfile, 'w')
            localFile.write(u.read())
            localFile.close()
            cleanup.append(_cssfile)
        else:
            _cssfile = css
        cssfile = open(_cssfile, 'r')
        css_def = cssfile.read()


    for (key, val) in images.items():
        htmlreport = htmlreport.replace(key, val)

    # render
    htmlreport = to_utf8(htmlreport)
    renderer = HTML(string=htmlreport, encoding='utf-8')
    pdf_fn = outfile if outfile else tempfile.mktemp(suffix=".pdf")
    if css:
        renderer.write_pdf(pdf_fn, stylesheets=[CSS(string=css_def)])
    else:
        renderer.write_pdf(pdf_fn)
    # return file data
    pdf_data = open(pdf_fn, "rb").read()
    if outfile is None:
        os.remove(pdf_fn)
    for fn in cleanup:
        os.remove(fn)
    return pdf_data

def localize_images(html):
    """The PDF renderer will attempt to retrieve attachments directly from the
    URL referenced in the HTML report, which may refer back to a single-threaded
    (and currently occupied) zeoclient, hanging it.  All images hosted via
    URLs that refer to the Plone site, must be converted to local file paths.

    This function modifies the URL of all images that can be resolved using 
    traversal from the root of the Plone site (eg, Image or File fields).
    It also discovers images in 'bika' skins folder and modifies their URLs.
    
    Other images may need to be handled manually.

    Returns a list of files which were created, and a modified copy
    of html where all remote URL's have been replaced with file:///...
    """
    cleanup = []
    _html = html.decode('utf-8')

    # get site URL for traversal
    portal = getSite()
    skins = portal.portal_skins
    portal_url = portal.absolute_url().split("?")[0]

    # all src="" attributes
    for match in re.finditer("""src.*\=.*(http[^'"]*)""", _html, re.I):
        url = match.group(1)
        filename = url.split("/")[-1]
        if filename == 'logo_print.png':
            logo = portal.unrestrictedTraverse('portal_skins/custom/logo_print.png')
            if hasattr(logo, 'filename'):
                filename = logo.filename
                data = str(logo._data)
            else:
                filename = attachment.__name__
                data = str(attachment.data)
            extension = "." + filename.split(".")[-1]
            outfile, outfilename = tempfile.mkstemp(suffix=extension)
            outfile = open(outfilename, 'wb')
            outfile.write(data)
            outfile.close()
            cleanup.append(outfilename)

        elif '++' in url:
            # Resource directories
            outfilename = resource_filename(
                'bika.lims', 'browser/images/' + filename)
        elif filename in skins['bika']:
            # portal_skins
            outfilename = skins['bika'][filename].filename
        else:
            # File/Image/Attachment fieldx
            att_path = url.replace(portal_url + "/", "").encode('utf-8')
            attachment = portal.unrestrictedTraverse(att_path)
            if hasattr(attachment, 'getAttachmentFile'):
                attachment = attachment.getAttachmentFile()

            filename = attachment.filename
            extension = "." + filename.split(".")[-1]
            outfile, outfilename = tempfile.mkstemp(suffix=extension)
            outfile = open(outfilename, 'wb')
            data = str(attachment.data)
            outfile.write(data)
            outfile.close()
            cleanup.append(outfilename)

        _html = _html.replace(url, "file://" + outfilename)
    return cleanup, _html
