#!/usr/bin/python
#
# lo-cybercompliance - LibreOffice extension for indicating compliance
# with named security requirements.
#
# Copyright 2015 Jared Jennings and Commons Machinery
#                <http://commonsmachinery.se/>
#
# Author(s): Artem Popov <artfwo@commonsmachinery.se>,
#            Peter Liljenberg <peter@commonsmachinery.se>,
#            Jared Jennings <jjennings@fastmail.fm>
#
# Distributed under the GPLv2 license; please see the LICENSE file for
# details.

from xml.dom import minidom
import tempfile, os
import uuid
import time
import pprint
import sys

import uno
import unohelper

from com.sun.star.awt import Size
from com.sun.star.awt import Point
from com.sun.star.task import XJob
from com.sun.star.task import XJobExecutor
from com.sun.star.beans import PropertyValue
from com.sun.star.io import XOutputStream

from com.sun.star.datatransfer import DataFlavor
from com.sun.star.datatransfer import XTransferable
from com.sun.star.datatransfer.clipboard import XClipboardOwner

from com.sun.star.lang import XInitialization
from com.sun.star.frame import XDispatch
from com.sun.star.frame import XDispatchProvider
from com.sun.star.ui import XContextMenuInterceptor
from com.sun.star.ui.ContextMenuInterceptorAction import IGNORED
from com.sun.star.ui.ContextMenuInterceptorAction import EXECUTE_MODIFIED
from com.sun.star.ui.ContextMenuInterceptorAction import CONTINUE_MODIFIED

from com.sun.star.datatransfer.dnd import XDropTargetListener
from com.sun.star.datatransfer.dnd.DNDConstants import ACTION_COPY

from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK
from com.sun.star.text.TextContentAnchorType import AS_CHARACTER
from com.sun.star.text.TextContentAnchorType import AT_PARAGRAPH
from com.sun.star.rdf.FileFormat import RDF_XML
from com.sun.star.rdf.URIs import ODF_PREFIX
from com.sun.star.ui.ActionTriggerSeparatorType import LINE

from com.sun.star.container import NoSuchElementException

BOOKMARK_BASE_NAME = "$metadata-tag-do-not-edit$"


class Metadata(object):
    """Helper functions for working with the RDF metadata APIs"""

    GRAPH_FILE = 'metadata/cybercompliance.rdf'
    GRAPH_TYPE_URI = 'http://securityrules.info/ns/cybercompliance/1#ComplianceStatements'

    def __init__(self, ctx, model):
        self.ctx = ctx
        self.model = model
        self.repository = self.model.getRDFRepository()

        # Load or create graph
        type_uri = self.uri(self.GRAPH_TYPE_URI)
        graph_uris = self.model.getMetadataGraphsWithType(type_uri)
        if graph_uris:
            graph_uri = graph_uris[0]
        else:
            graph_uri = self.model.addMetadataFile(self.GRAPH_FILE, (type_uri, ))

        self.graph = self.repository.getGraph(graph_uri)


    def uri(self, uri):
        return self.ctx.ServiceManager.createInstanceWithArguments(
            "com.sun.star.rdf.URI", (uri, ))

    def literal(self, value):
        return self.ctx.ServiceManager.createInstanceWithArguments(
            "com.sun.star.rdf.Literal", (value, ))

    def add_statement(self, subject, predicate, obj):
        self.graph.addStatement(subject, predicate, obj)

    def add_rdfa_statements(self, subject, predicates, literal):
        self.repository.setStatementRDFa(subject, predicates, literal, '', None)

    def create_meta_element(self):
        return self.model.createInstance('com.sun.star.text.InContentMetadata')

    def dump_graph(self):
        statements = self.repository.getStatements(None, None, None)
        while statements.hasMoreElements():
            s = statements.nextElement()
            self.dump_statement(s)

    def dump_statement(self, s):
        if hasattr(s.Object, 'Value'):
            obj = '"{0}"'.format(s.Object.Value)
        else:
            obj = '<{0}>'.format(s.Object.StringValue)

        if s.Graph:
            g = s.Graph.StringValue
        else:
            g = 'RDFa'

        print('<{0}> <{1}> {2} . # {3}'.format(
                s.Subject.StringValue,
                s.Predicate.StringValue,
                obj, g))


class DocumentsJob(unohelper.Base, XJobExecutor):

    DOCUMENTS = 'http://securityrules.info/ns/cybercompliance/1#documents'
    TEXT_PREFIX = 'In accordance with '

    def __init__(self, ctx):
        self.ctx = ctx

    def trigger(self, args):
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)

        model = desktop.getCurrentComponent()
        controller = model.getCurrentController()

        if model.supportsService("com.sun.star.text.TextDocument"):
            clip = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.datatransfer.clipboard.SystemClipboard", self.ctx)
            contents = clip.getContents()
            data_flavors = contents.getTransferDataFlavors()
            mimeTypes = [d.MimeType for d in data_flavors]
            if 'text/plain;charset=utf-8' in mimeTypes:
                text_clip = next(d for d in data_flavors
                                 if d.MimeType == 'text/plain;charset=utf-8')
                text = clip.getContents().getTransferData(text_clip).value.decode('UTF-8')
                if text.startswith('http://') or text.startswith('https://'):
                    requirement_uri = text
                    requirement_name = text.split('/')[-1]
                else:
                    return
            else:
                return
                

            # Metadata is only supported in text documents
            metadata = Metadata(self.ctx, model)

            # duplicate current cursor
            view_cursor = controller.getViewCursor()
            cursor = view_cursor.getText().createTextCursorByRange(view_cursor)
            cursor.gotoStartOfSentence(False)
            text = model.Text

            text.insertString(cursor, "(", False)

            metafield = model.createInstance("com.sun.star.text.textfield.MetadataField")
            text.insertTextContent(cursor, metafield, False)
            mfcursor = metafield.createTextCursor()

            metadata.add_statement(metafield,
                                   metadata.uri(self.DOCUMENTS),
                                   metadata.uri(requirement_uri))
            metadata.add_statement(metafield,
                                   metadata.uri(ODF_PREFIX),
                                   metadata.literal(self.TEXT_PREFIX + requirement_name))

            
            text.insertString(cursor, ")", False)

            # DEBUG:
            metadata.dump_graph()
            

# http://www.oooforum.org/forum/viewtopic.phtml?t=82016
# https://www.openoffice.org/api/docs/common/ref/com/sun/star/datatransfer/dnd/module-ix.html
#
# the Context of an event we receive contains the methods that we call
# to make things happen or not happen regarding the drag or drop
class DTLCyberCompliance(unohelper.Base, XDropTargetListener):
    DOCUMENTS = 'http://securityrules.info/ns/cybercompliance/1#documents'
    TEXT_PREFIX = 'In accordance with '

    SUPPORTED_MIME_TYPES = (
        'text/plain;charset=utf-8',
    )

    def __init__(self, ctx):
        self.accepting = True
        self.ctx = ctx
        super(DTLCyberCompliance, self).__init__()

    def drop(self, event):
        print 'drop'
        t = event.Transferable # has the data to be dropped
        for flavor in t.getTransferDataFlavors():
#            print flavor, t.getTransferData(flavor)
            if flavor.MimeType in self.SUPPORTED_MIME_TYPES:
                event.Context.acceptDrop(event.DropAction)
                # the data is a ByteSequence; it has a value attribute
                data = t.getTransferData(flavor).value
                break
        else:
            print "rejected!"
            event.Context.rejectDrop()
            return
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)
        model = desktop.getCurrentComponent()
        controller = model.getCurrentController()
        if not model.supportsService("com.sun.star.text.TextDocument"):
            event.Context.dropComplete(False)
            return
        # text/uri-list specifies that the URIs in it are URIs not
        # IRIs, so they will be ASCII, possibly with punycode and tons
        # of percent-encoded stuff, but ASCII.
        print repr(data)
        text = bytes(data).decode('UTF-8')
        print repr(text)
        for line in text.split('\n'):
            if line.startswith('http://') or line.startswith('https://'):
                requirement_uri = line
                requirement_name = line.split('/')[-1]
                break
        else:
            event.Context.dropComplete(False)
            return
        # Metadata is only supported in text documents
        metadata = Metadata(self.ctx, model)
        # duplicate current cursor
        view_cursor = controller.getViewCursor()
        cursor = view_cursor.getText().createTextCursorByRange(view_cursor)
        cursor.gotoStartOfSentence(False)
        text = model.Text
        text.insertString(cursor, "(", False)
        metafield = model.createInstance("com.sun.star.text.textfield.MetadataField")
        text.insertTextContent(cursor, metafield, False)
        mfcursor = metafield.createTextCursor()
        metadata.add_statement(metafield,
                               metadata.uri(self.DOCUMENTS),
                               metadata.uri(requirement_uri))
        metadata.add_statement(metafield,
                               metadata.uri(ODF_PREFIX),
                               metadata.literal(self.TEXT_PREFIX + requirement_name))
        text.insertString(cursor, ")", False)
        # DEBUG:
        metadata.dump_graph()
        event.Context.dropComplete(True)

    def dragEnter(self, event):
        print "dragEnter"
        for flavor in event.SupportedDataFlavors:
            if flavor.MimeType in self.SUPPORTED_MIME_TYPES:
                print "accepting!"
                self.accepting = True
                event.Context.acceptDrag(event.DropAction)
                break
        else:
            print "rejected!"
            self.accepting = False
            event.Context.rejectDrag()

    def dragExit(self, event):
        pass

    def dragOver(self, event):
        # we should only have to accept it once in dragEnter - but
        # sometimes it seems that is not enough. so accepting it here
        # if we accepted it there should be superfluous but it appears
        # to work and doesn't seem too slow.
        if self.accepting:
            event.Context.acceptDrag(event.DropAction)
        else:
            event.Context.rejectDrag()

    def dropActionChanged(self, event):
        pass


g_ImplementationHelper = unohelper.ImplementationHelper()

g_ImplementationHelper.addImplementation(
    DocumentsJob,
    'info.securityrules.extensions.cybercompliance.DocumentsJob',
    ('com.sun.star.task.Job',)
)


if __name__ == "__main__":
    import sys
    import time

    localContext = uno.getComponentContext()
    resolver = localContext.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", localContext)

    # connect to the running office, start as:
    #     soffice "--accept=socket,host=localhost,port=2002;urp;" --writer
    ctx = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
    smgr = ctx.ServiceManager

    cmd = sys.argv[1]
    if cmd == 'documents':
        job = DocumentsJob(ctx)
        job.trigger(None)

    elif cmd == 'drop':
        desktop = smgr.createInstanceWithContext(
            "com.sun.star.frame.Desktop", ctx)
        model = desktop.getCurrentComponent()
        panel = model.CurrentController.Frame.ComponentWindow
        scroll_pane = panel.AccessibleContext.getAccessibleChild(0)
        docview = scroll_pane.AccessibleContext.getAccessibleChild(0)
        dtlcc = DTLCyberCompliance(ctx)
        number_to_name = {
            49: 'ROOT_PANE',
            50: 'SCROLL_BAR',
            51: 'SCROLL_PANE',
            13: 'DOCUMENT',
            56: 'SPLIT_PANE',
            40: 'PANEL',
            17: 'FILLER',
            77: 'RULER',
            13: 'DOCUMENT',
            44: 'PUSH_BUTTON',
        }
        def for_self_droptarget_and_subwindows(w, methodname, depth, *args):
            c = w.AccessibleContext
            role = c.getAccessibleRole()
            if role == 40:
                dt = w.Toolkit.getDropTarget(w)
                getattr(dt, methodname)(*args)
            try:
                for w_ in w.Windows:
                    for_self_droptarget_and_subwindows(w_, methodname, depth+1, *args)
            except AttributeError:
                pass
        for_self_droptarget_and_subwindows(panel, 'addDropTargetListener', 0, dtlcc)
        print "installed"
        try:
            time.sleep(300000)
        except KeyboardInterrupt:
            pass
        print "removing"
        for_self_droptarget_and_subwindows(panel, 'removeDropTargetListener', 0, dtlcc)
    else:
        print("unknown command", cmd)

    # Python-UNO bridge workaround: call a synchronous method, before the python
    # process exits to sync the remote-bridge cache, otherwise an async call
    # may not terminate properly.
    ctx.ServiceManager

