---
# markdown static site generator

**m**arkdown **s**tatic **s**ite generator is a simple program that generates
a static HTML website from content written in Markdown. It uses YAML for
configuration and jinja2 for templating.

There are plenty of similar tools available; mdss is intended as a simple
alternative that requires little configuration or additional markup in your
content files.

## Content

### Pages

Pages consist of two parts -- the *context* section (written in YAML) and
the *content* section (written in Markdown). The two sections are separated by
a line containing `---`.

The *context* is used to render the template, and the *content* section is
converted to HTML and made available as `content` in the template context.

Here's an example:

    title: Example page
    template: my-template.html
    tags:
      - example
      - mdss
      - markdown
    ---
    This example uses *markdown*

A simple example of `my-template.html` could be:

```html
<html>
    <head>
        <title>{{ title }}</title>
    </head>
    <body>
        <h1>{{ title }}</h1>
        {{ content }}

        <div>
            Tags: {{ tags|join(", ") }}
        </div>
    </body>
</html>
```

Some variables in the context section are recognised by mdss and have special
meaning:

| Variable | Description |
| -------- | ----------- |
| template | The template to render the page with. This must be a filename found in one of the `template_path` directories (see [site configuration](#site-configuration)) |
| macros   | Python functions(s) that can be used as macros in the content section. See [macros](#macros) for examples. |

### Templates

Templates are rendered using jinja2. Each template is rendered using the
context section of the content pages.

Some additional variables are set by mdss itself:

| Variable    | Description |
| ----------- | ----------- |
| title       | Title based on the filename of the content file (if not already set) |
| breadcrumbs | [Breadcrumbs](http://ui-patterns.com/patterns/Breadcrumbs) as a list of pages starting with the home page and ending with current page. Each page has properties `path` (relative URL to page) and `title` |
| children    | List of child pages sorted by title. Each item in the list has properties `path`, `title` and `children` (loop through the `children` property recursively to get *all* pages beneath this one in the hierarchy) |

### Directory structure

Content is structured in a hierarchical manner that can go as many layers deep
as you want. Consider the following directory structure

    example-site/
    ├── blog
    │   ├── 2018
    │   │   ├── june
    │   │   │   └── second-post.md
    │   │   └── may
    │   │       └── first-post.md
    │   └── index.md
    └── my-page.md

This translate to the following HTML pages:

    exported-site/
    ├── blog
    │   ├── 2018
    │   │   ├── index.html
    │   │   ├── june
    │   │   │   ├── index.html
    │   │   │   └── second-post
    │   │   │       └── index.html
    │   │   └── may
    │   │       ├── first-post
    │   │       │   └── index.html
    │   │       └── index.html
    │   └── index.html
    ├── index.html
    └── my-page
        └── index.html

Note that `index.html` pages have been created for `blog`, `2018`, `may`, and
`june`, even though no `index.md` files were present. This is because these
directories have pages 'beneath' them. This allows you to have automatic
index pages that show a list of child pages.

### Macros

To avoid repeating HTML throughout your content, python functions may be used
as *macros* to substitute text with the return value of the function. For
example:

    title: Macro example
    macros: |
        def math_block(string, title="", type="Definition"):
            return ("<h2 class='maths-header'>{type}: {title}</h2>"
                    "<div class='maths-body'>{string}</div>").format(**locals())
    ---

    <?math_block title="Continuous function">
        A function f is continous at x if ...
    <?/math_block>

    <?math_block title="Intermediate value theorem" type="Theorem">
        For a function f continous on [a, b] ...
    <?/math_block>

The `content` variable in the template context will then contain

```html
<h2 class='maths-header'>Definition: Continuous function</h2>

<div class='maths-body'>
    A function f is continous at x if ...
</div>

<h2 class='maths-header'>Theorem: Intermediate value theorem</h2>

<div class='maths-body'>
    For a function f continous on [a, b] ...
</div>
```

Multiple functions can be defined in the `macros` section. Each function should
take a single positional argument (the value between `<?name>` and `<?/name>`
for a function `name`), and may optionally accept keyword arguments.

Keyword arguments are given as normal HTML attributes -- they may be quoted
with single or double quotes, or not quoted at all. Note that arguments are
always passed as *strings*.

## Site configuration

Site-wide configuration options can be set in `mdss_config.yml` at the root
level of the directory containing content. The `mdss` command finds this file
by traversing up the filesystem starting in the current directory (similar to
how Git finds the `.git` directory). To use another name, give the path to the
config explicitly with the `-f` option.

The available config options are:

| Variable         | Description |
| --------         | ----------- |
| templates_path   | List of directories to search for templates in (default: `["templates"]`) |
| default_template | Name of the template to use when one is not specified. This is required for pages generated automatically because they have child pages (default: `base.html`) |
| default_context  | A dict used as the default context for each page |
