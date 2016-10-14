
---
cms is a content management system that creates a static website from files
written in [Markdown](https://daringfireball.net/projects/markdown/) and
[YAML](http://yaml.org). Its aim is to get in the way as little as possible,
whilst still being fairly flexible.

cms is written in Python using [Flask](http://flask.pocoo.org/).

## Configuration
Site-wide configuration is specified in a YAML file. The following options are
available:

* **content_dir:** The directory where the pages are located

* **template_dir** (optional): The directory where custom templates are located
  (defaults to the same as `content_dir`). Note that templates will also be
  loaded from `default_templates` in the same directory as cms.

* **static_dir** (optional):  The directory where custom static files (e.g. images,
  js, css) are located (defaults to the same as `content_dir`). Note that static
  files will also be served from `default_static` in the same directory as cms.

* **host** (optional): The host address to listen on (defaults to localhost)

* **port** (optional): The port to listen on (defaults to 5000)

* **default_page_config** (optional): This is the default config that is used as a base
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
    configuration options for the page. The options specified here are passed as
    variable to the page template, so which options you need to specify depends
    on what your template looks like!

    However, some options are special and are used by cms itself:

    * **template** (required): The template to use to render the page. This should be a
    filename relative to one of the templates directories.

    * **base_config:** A file to inherit the config section from. The entire
      config section from the parent page is loaded, and the rest of the config
      from the child page is merged in. For list and dictionary options, the
      options in the child page are appended to the list or dictionary. For
      string options the parent config is overwritten. This option should be a
      filename relative to the content directory.

    * **custom_elements:** This option is best explained with an example:

            custom_elements:
              myelement: "<div class='myelem'>Contents is: $</div>"
            ---
            <myelement>hello</myelement>

          The resulting HTML would then be

               <div class='myelem'>Contents is: hello</div>

          This option can be used like a macro to avoid writing too much HTML
          in your Markdown.

    * **page_order:** For index pages (i.e ones with other pages beneath), this
      is a list specifying the order of child pages in the [site index](#site-index).
      Any pages not included here will put be put in alphabetical order at the
      end.

* **Content section**

    This section contains the actual content for the page, written in Markdown.

## Templates

cms uses [jinja2](http://jinja.pocoo.org/docs/dev/) to render templates. Any
option specified in the [config section](#page-config) of a page is passed
as a variable to the template. In addition, cms adds some variables itself:

* **content:** This contains the contents of the page (from the contents
section) as HTML. You will *need* to use this one in your templates, as
there will be no content on the page otherwise.

* **title:** If not already specifed in the page config, cms will set this to a
default value for the page title based on the filename. It does this by replacing
hyphens and underscores with spaces and capitalising the first letter.

* <span id="site-index">**site_index:**</span> This is a list containing information about the page heirarchy
for the site. Each page is a dictionary of the form:

        {"title": <page title based on filename>,
         "url": <URL for the page>,
         "path": <path to file for the page>,
         "children": [<child pages>]}

    Where `children` is a list of child pages in the same format.

* **sub_index:** This is a list in the same format as `site_index` that only
  includes pages beneath the current page in the navigational heirarchy. This
  variable is only present when the page is an index page.

* **header_links:** This is a list in the same format as `site_index` and
can be used to construct a menu for the site. Currently this is the same as
`site_index`.

* **breadcrumbs:** This is a list of pages in the same format as `site_index`
that shows the location of the current page in the heirarchy. The top level page
is first, and the current page is last. See
[here](http://ui-patterns.com/patterns/Breadcrumbs) for info about breadcrumbs.

* <span id="index-page-option">**index_page:**</span> If a page is an index page
(i.e. it is called index.md and there are other pages beneath it), this will be
set to True

## Static files

Static files such as images, js scripts, css files and such should be placed in
the folder specifed by `static_dir` in the site-wide config file. Such files can
then be accessed via the URL `/<file>`, where `<file>` is the file path
relative to `static_dir`.