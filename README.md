lo-cybercompliance
==================

LibreOffice extension for indicating compliance with named security requirements.

See issues, to-dos and ideas on the Trello board at
https://trello.com/b/lD7Nleel/lo-cybercompliance.


Use case
--------

You're writing some documents which lay out how you comply with some
requirements previously set out and given names by someone else. These
requirements vary in detail and scope. At least one of the documents
you are writing is in LibreOffice Writer or OpenOffice Writer. You
want to indicate your compliance in a way that makes sense when you
are writing the details, but will later let you summarize and
demonstrate compliance as automatically as possible. For
maintainability, you don't want to have to order your document by
requirement names.

If those things are true about you, this extension is for you.

Install the extension. Find a requirement that has a URI and get that
URI on the clipboard. Look, for example, at
http://securityrules.info/about/xugom-degub-tevab-mefex; right-click
one of the purple links at the right, like "V-13036," and copy the
[link
location](http://securityrules.info/id/xugom-degub-tevab-mefex/V-13036)
to the clipboard. Now, in LibreOffice, open the Compliance menu and
choose Documents to indicate that you are about to write documentation
that fulfills the requirement. A field appears in your document, which
looks like "(In accordance with V-13036)." After this, write, "The
list of DNS administrators is as follows: ..."  (because what V-13036
requires is that a list of DNS administrators be maintained).

Now your document contains not only the text "(In accordance with
V-13036)," but also some metadata you don't see, which indicates that
your document fulfills that rule, and can be easily pulled out later
by a script, and interesting things can be done with it.


License
-------

Copyright 2015 Jared Jennings and Commons Machinery
               <http://commonsmachinery.se/>

Author(s): Jared Jennings <jjennings@fastmail.fm>,
           Artem Popov <artfwo@commonsmachinery.se>,
           Peter Liljenberg <peter@commonsmachinery.se>
	   

Distributed under the GPLv2 license; please see the LICENSE file for
details.


White helmet and checkmark icon: Copyright 2015 Jared Jennings
<jjennings@fastmail.fm>.  CC Attribution-ShareAlike 4.0
<http://creativecommons.org/licenses/by-sa/4.0/>.  Based on
<https://www.flickr.com/photos/solhelmet/6719156327> by solhelmet and
<http://pixabay.com/en/quality-hook-check-mark-ticked-off-500950/>.
