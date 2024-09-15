# Calibre plugin for legie.info

**1st version created by Missha** - please see: [here]( https://www.mobileread.com/forums/showthread.php?t=184494)

**From version 2.0.3 expanded and maintained by seeder** - please see: [here](https://www.mobileread.com/forums/showthread.php?t=362097)

Legie is a Czech site focused on sci-fi and fantasy readers and collecting information about books published in the Czech Republic and Slovakia. The whole site is in Czech only, so this plugin will be used mainly by Czech or Slovak readers.

This plugin uses legie.info as a metadata source.

## Main Features:

#### Basics
Can retrieve all basic metadata for books: title, authors, rating (*), series (including index), tags (genres), publisher, published date, language,        comments (book description) and cover
#### Tales and poems
Can search for tales and poems. Saves all available information into basic metadata:
title, authors, rating (*), comments (tale/poem description),
books including tale/poem into Tags, original title into Publisher and original published year into Published
#### Identifiers
Can retrieve legie (for books), legie_povidka (for tales/poems) and ISBN identifiers
#### Title identifiers
User can add identifier into Title before searching in format 'legie:123' and it will be used for search prior embedded identifier.
User can specify year of book issue (published edition) in Title too with 'pubdate:2023' or 'pubyear:2023' format. Closest issue will be chosen then.
With 'lang:cs' or 'language:sk' user can specify language of wanted book issue.
User can specify publisher of book issue (published edition) in Title too with 'publisher:Name_of_publisher' format.
publisher and pubdate/pubyear.
Title identifiers can be combined together. Title identifiers are used for ordering search results too.
#### Search engine
Can choose which engine will be used for search. Google search, DuckDuckGo and Legie built-in search supported.
#### Search priority
User can disable certain search attempts in search queue (Searching by identifier then by ISBN then search for Tales/poems then for books with Title/Authors combinations).
#### Book issues
User can choose which book issue (published edition) they prefer (Czech or Slovak and newest or oldest).
#### Multiple covers
Can download multiple covers based on selected preferred issue (Czech or Slovak).
Can download additional book cover from obalkyknih.cz site using ISBN number.
#### Additional metadata
Plugin can add additional metadata founded on site into Basic metadata fields:
- real (non pseudo) author names, translators, book cover authors and illustrators into Authors field
- first publication date into Published field
- genres, tags, pages, print run, cover type, first pubdate, pubdate, original title, title, authors, translators, book cover authors, illustrators, series (with index), book edition (with index), rating (%), rating (0-5), rating (0-10), rating count, ISBN, legie ID, book awards and book tales/poems list into Tags field and into specific ("leg_" prefixed) Identifiers
- genres, tags, pages, print run, cover type, first pubdate, pubdate, original title, title, authors, translators, book cover authors, illustrators, series (and index), book edition (and index), rating (%), rating (0-5), rating (0-10), rating count, ISBN and legie ID into Title and Publisher field
- genres, tags, pages, print run, cover type, first pubdate, pubdate, original title, title, authors, translators, book cover authors, illustrators, series (with index), book edition (with index), rating (%), rating (0-5), rating (0-10), rating count, ISBN, legie ID, book awards, book tales/poems list and trivia into Comments field
#### Comment, title, series and publisher builder
When adding additional metadata to comments, title, series or publisher, you can choose the order in which the information is assembled in that field.
#### Metadata mappings
Plugin can remap downloaded information from genres/tags, series/editions and publishers into user specified version.
Added filter for saving only mapped items (all other will be removed).
#### Other
- Max search results limit
- Swap FN LN into 'LN FN' (similar to built-in 'LN, FN' with comma) in Authors
- Save only first name into Authors
- Save authors role
- Plugin translated into: English, Czech


## Installation Notes:
- Download the attached zip file and install the plugin as described in the Introduction to plugins thread.
- Note that this is not a GUI plugin so it is not intended/cannot be added to context menus/toolbars etc.
- Customize other options from the Metadata download configuration screen ("Configure download metadata" button).


## Special Notes:
- Required calibre version is 0.8.0 and higher.
- Recommended to set up before the first use.

