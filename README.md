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

### Templates

Templates are rendered using jinja2. Each template is rendered using the
context section of the content pages.

Some additional variables are set by mdss itself:

| Variable | Description |
| -------- | ----------- |
| title    | Title based on the filename of the content file (if not already set) |

## Directory structure

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
