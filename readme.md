
---
cms is a content management system that creates a website from static files
written in [Markdown](https://daringfireball.net/projects/markdown/) and
[YAML](http://yaml.org). Its aim is to get in the way as little as possible, whilst still being fairly flexible.

## Configuration
Site-wide configuration is specified in a YAML file. The following options are
available:

* **default_page_config:** This is the default config that is used as a base
  for every page on the site (see [below](#page-config))

## Content
Content is structured in a heirarchal manner that can go as many layers deep as you
want. Consider the following directory structure

    ./articles
    ./articles/article1.md
    ./articles/blog
    ./articles/blog/index.md
    ./articles/blog/blogpost1.md
    ./page.md

This translate to pages with the following URLs:

* /articles
* /articles/article1
* /articles/blog
* /articles/blog/blogpost1
* /page

Note that even though there is no `articles/index.md` there is still a page for
articles - this is because there are pages 'beneath' it. In this case the
`index_page` flag will be set in the template (see [below](#index-page-option)).

## Pages
Each page is contained in a file ending in `.md`. This file consists of two
section, the *config section* and *content section*. The two sections are
separated by a line containing the string `---`.

* <span id="page-config">**Config section**</span>

    This section is written in YAML and defines various
    configuration options for the page. The options specified here are passed to
    the templating engine to render the page template, so which
    options you need to specify depends on what your template looks like!

    However some options are special and are used by cms itself:

    * **template:** The template to use to render the page. This should be a
    filename relative to the templates directory.

    * **base_config:** This option allows a page to inherit a config section from
      another page. The entire config section from the parent page is loaded,
      and the rest of the config from the child page is merged in. For list and
      dictionary options, the options in the child page are appended to the list
      or dictionary. For string options the parent config is overwritten.

    * **custom_elements:** This option is best explained with an example:

            custom_elements:
              myelement: "<div class='myelem'>Contents is: $</div>"
            ---
            <myelement>hello</myelement>

          The resulting HTML would then be

               <div class='myelem'>Contents is: hello</div>

          This option can be used like a macro to avoid writing too much HTML
          in your Markdown.

          One caveat is that the content between custom element tags will **NOT**
          be converted from Markdown, so you will have to use HTML for any
          formatting.

    cms will also add some extra options that will be passed to the templating
    engine that you may wish to make use of:

    * **content:** This contains the contents of the page (from the contents
    section) as HTML. You will *need* to use this one in your templates, as
    there will be no content on the page otherwise.

    * **title:** If not already specifed, cms will set this to a default
    value for the page title based on the filename. It does this by replacing
    hyphens and underscores with spaces and capitalising the first letter. If you
    want to make use of this feature then make sure to use `title` as the variable
    for the page title in your templates.

    * **site_index:** This is a list containing information about all pages on
    the site. Each page is a dictionary in the format:

            {"title": <page title based on filename>,
             "url": <URL for the page>,
             "path": <path to file for the page>,
             "children": [<child pages>]}

    * **header_links:** This is a list in the same format as `site_index` and
    can be used to construct a menu for the site. Currently this is the same as
    `site_index` but only goes two levels deep.

    * **breadcrumbs:** This is a list of pages in the same format as `site_index`
    that shows where the current page is in the heirarchy. The top level page
    is first, and the current page is last. See [here](http://ui-patterns.com/patterns/Breadcrumbs) for info about breadcrumbs.

    * <span id="index-page-option">**index_page:**</span>If a page is an index page (i.e. it is called index.md and
    there are other pages beneath it), `index_page` will be set to True.

* **Content section**

    This section contains the actual content for the page, written in Markdown.
