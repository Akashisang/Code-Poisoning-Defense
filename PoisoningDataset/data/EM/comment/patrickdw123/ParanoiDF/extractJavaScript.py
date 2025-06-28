#    ParanoiDF. A combination of several PDF analysis/manipulation tools to 
#    produce one of the most technically useful PDF analysis tools.
#    
#    Idea proposed by Julio Hernandez-Castro, University of Kent, UK.
#    By Patrick Wragg
#    University of Kent
#    21/07/2014
#    
#    With thanks to:
#    Julio Hernandez-Castro, my supervisor. 
#    Jose Miguel Esparza for writing PeePDF (the basis of this tool).
#    Didier Stevens for his "make-PDF" tools.
#    Blake Hartstein for Jsunpack-n.
#    Yusuke Shinyama for Pdf2txt.py (PDFMiner)
#    Nacho Barrientos Arias for Pdfcrack.
#    Kovid Goyal for Calibre (DRM removal).
#    Jay Berkenbilt for QPDF.
#
#    Copyright (C) 2014-2018 Patrick Wragg
#
#    This file is part of ParanoiDF.
#
#        ParanoiDF is free software: you can redistribute it and/or modify
#        it under the terms of the GNU General Public License as published by
#        the Free Software Foundation, either version 3 of the License, or
#        (at your option) any later version.
#
#        ParanoiDF is distributed in the hope that it will be useful,
#        but WITHOUT ANY WARRANTY; without even the implied warranty of
#        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
#        GNU General Public License for more details.
#
#        You should have received a copy of the GNU General Public License
#        along with ParanoiDF. If not, see <http://www.gnu.org/licenses/>.
#
#    This was written by Blake Hartstein as a part of Jsunpack-n.

'''
Blake Hartstein v0.1c (beta) pdf parser
Goal: extract all javascript from a pdf file
Revised Goal: extract other malicious parts of a pdf file too
Jan 19, 2010

Command line usage:
$ ./pdf.py [pdf file]

Updated 2013-04-11 Thanks for the contributions from David Dorsey of visiblerisk.com
'''