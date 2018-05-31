import time
import os

import yaml
import pytest
from py.path import local

from mdss.site_gen import SiteGenerator
from mdss.tree import SiteTree
from mdss.config import SiteConfig, ConfigOption
from mdss.page import Page, HomePage, PageInfo, cachedproperty
from mdss.exceptions import InvalidPageError


class TestSiteGeneration(object):

    def test_site_gen(self, tmpdir):
        files = []
        content = tmpdir.mkdir("content")
        templates = tmpdir.mkdir("templates")
        templates.join("t.html").write("hello")

        # single file
        files.append(content.join("food.md"))

        # automatic index creation
        m = content.mkdir("music")
        files.append(m.join("guitar.md"))
        files.append(m.join("piano.md"))

        # explicit index page
        b = content.mkdir("blog")
        files.append(b.join("index.md"))

        # home page
        files.append(content.join("index.md"))

        # deeper nesting
        d1 = content.mkdir("d1")
        d2 = d1.mkdir("d2")
        d3 = d2.mkdir("d3")
        files.append(d2.join("two.md"))
        files.append(d3.join("three.md"))

        for f in files:
            f.write("---\n")

        config = SiteConfig(templates_path=[str(templates)],
                            default_template="t.html")
        s = SiteGenerator(str(content), config)
        output = tmpdir.mkdir("output")
        s.gen_site(str(output))
        all_files = []
        for dirpath, dirnames, filenames in os.walk(str(output)):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                all_files.append(os.path.relpath(path, start=str(output)))

        assert set(all_files) == set([
            "index.html",
            "blog/index.html",
            "music/index.html",
            "music/guitar/index.html",
            "music/piano/index.html",
            "food/index.html",
            "d1/index.html",
            "d1/d2/index.html",
            "d1/d2/two/index.html",
            "d1/d2/d3/index.html",
            "d1/d2/d3/three/index.html"
        ])

    def test_breadcrumbs(self, tmpdir):
        templates = tmpdir.mkdir("templates")
        templates.join("b.html").write("\n".join([
            "{% for b in breadcrumbs %}",
                "{{ b.path }}, {{ b.title }}",
            "{% endfor %}"
        ]))

        tests = []
        home_bc = [("/", HomePage.title)]
        tests.append(("index.md", home_bc))

        books_bc = home_bc + [("/books/", "Books")]
        tests.append(("books.md", books_bc))

        music_bc = home_bc + [("/music/", "Music")]
        tests.append(("music.md", music_bc))

        guitar_bc = music_bc + [("/music/guitar/", "Guitar")]
        tests.append(("music/guitar.md", guitar_bc))

        piano_bc = music_bc + [("/music/piano/", "Piano")]
        tests.append(("music/piano/index.md", piano_bc))

        chopin_bc = piano_bc + [("/music/piano/chopin/", "Chopin")]
        tests.append(("music/piano/chopin.md", chopin_bc))

        content = tmpdir.mkdir("content")
        for path, _ in tests:
            dirname = os.path.join(str(content), os.path.dirname(path))
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            content.join(path).write("---")

        config = SiteConfig(templates_path=[str(templates)],
                            default_template="b.html")
        s_gen = SiteGenerator(str(content), config=config)

        output = tmpdir.mkdir("output")
        s_gen.gen_site(str(output))

        for src_path, expected_breadcrumbs in tests:
            dest_path = src_path.replace("md", "html")
            if not dest_path.endswith("index.html"):
                dest_path = os.path.join(dest_path[:-5], "index.html")

            with open(os.path.join(str(output), dest_path)) as f:
                contents = f.read().strip()

            lines = filter(None, contents.strip().split("\n"))
            assert list(lines) == [p + ", " + t for p, t in expected_breadcrumbs]

    def test_split_path(self):
        def t(p): return SiteGenerator.split_path(p)
        assert t("/one/two/three/four.md") == ["one", "two", "three",
                                               "four.md"]
        assert t("/one/two/three/") == ["one", "two", "three"]
        assert t("relative/path/to/file.html") == ["relative", "path", "to",
                                                   "file.html"]
        assert t("relative/dir/") == ["relative", "dir"]


class TestPageRendering(object):

    @pytest.fixture
    def site_setup(self, tmpdir):
        templates = tmpdir.mkdir("templates")
        templates.join("def.html").write("{{ content }}")

        content = tmpdir.mkdir("content")
        output = tmpdir.mkdir("output")
        config = SiteConfig(templates_path=[str(templates)],
                            default_template="def.html")
        s_gen = SiteGenerator(str(content), config)
        return templates, content, output, s_gen


    def create_test_page(self, tmpdir, page_id="test", contents_str=None,
                         context={}, content=None):
        tmp_file = tmpdir.join("test_page_{}.md".format(time.time()))

        if not contents_str:
            contents_str = yaml.dump(context)
            contents_str += os.linesep + Page.SECTION_SEPARATOR + os.linesep
            contents_str += content

        tmp_file.write(contents_str)
        return Page(page_id, src_path=str(tmp_file))

    def test_page_rendering(self, tmpdir):
        """
        End to end test of page rendering
        """
        templates = tmpdir.mkdir("templates")
        templates.join("t123.html").write("\n".join([
            "<h1>{{ title }}</h1>",
            "<p>this is the default</p>"
        ]))

        templates.join("my-temp.html").write("\n".join([
            "<h1>{{ title }}</h1>",
            "<p>some cool template: {{ extra_var }}</p>",
            "{{ content }}"
        ]))

        content = tmpdir.mkdir("content")
        blog = content.mkdir("blog")
        blog.join("easter_2018.md").write("\n".join([
            "title: what i did on easter sunday",
            "template: my-temp.html",
            "extra_var: 42",
            "---",
            "page contents here"
        ]))

        config = SiteConfig(templates_path=[str(templates)],
                            default_template="t123.html")
        s_gen = SiteGenerator(content_dir=str(content), config=config)

        output = tmpdir.mkdir("output")
        out_dir = str(output)
        s_gen.gen_site(out_dir)

        def t(*x): return os.path.join(out_dir, *x)
        blog_index = t("blog", "index.html")
        easter_blog = t("blog", "easter_2018", "index.html")

        assert os.path.isfile(blog_index)
        assert os.path.isfile(easter_blog)

        with open(blog_index) as f:
            blog_index_str = f.read().strip()
        with open(easter_blog) as f:
            easter_blog_str = f.read().strip()

        assert blog_index_str == "\n".join([
            "<h1>Blog</h1>",  # title should have been capitalised
            "<p>this is the default</p>"
        ])

        assert easter_blog_str == "\n".join([
            "<h1>what i did on easter sunday</h1>",
            "<p>some cool template: 42</p>",
            "<p>page contents here</p>"
        ])

    def test_invalid_page_content(self, tmpdir):
        content_tmp = tmpdir.mkdir("content_tmp")
        files = {
            "no-sep": [
                "title: no separator",
                "template: t.html",
                "this is the content"
            ],
            "invalid-yaml": [
                "title: blah",
                "template: t.html",
                "{hello",
                "---",
                "this is the content"
            ]
        }
        pages = []
        for name, lines in files.items():
            tmp_file = content_tmp.join("{}.md".format(name))
            tmp_file.write("\n".join(lines))
            with pytest.raises(InvalidPageError):
                Page(name, src_path=str(tmp_file))

    def test_markdown_conversion(self, tmpdir):
        templates = tmpdir.mkdir("templates")
        templates.join("t.html").write("{{ content }}")
        config = SiteConfig(default_template="t.html",
                            templates_path=[str(templates)])

        page = self.create_test_page(tmpdir,
                                     content="This should be **Markdown**")
        s_gen = SiteGenerator(content_dir=None, config=config)
        expected_html = "<p>This should be <strong>Markdown</strong></p>"
        assert s_gen.render_page(page) == expected_html

    def test_title_handling(self, tmpdir):
        """
        Check that a title is generated based on filename if title not
        specified in page context.

        Check that if a title is specified it is used in breadcrumbs
        """
        templates = tmpdir.mkdir("templates")
        templates.join("t.html").write("{{ title }}")
        templates.join("b.html").write(
            "{{ breadcrumbs|map(attribute='title')|join(', ') }}"
        )
        config = SiteConfig(default_template="t.html",
                            templates_path=[str(templates)])

        content = tmpdir.mkdir("content")
        with_title = content.mkdir("with-title")
        with_title.join("index.md").write("\n".join([
            "template: t.html",
            "title: custom title",
            "---"
        ]))
        with_title.join("child.md").write("\n".join([
            "template: b.html",
            "title: woohoo",
            "---"
        ]))
        content.join("without-a-title.md").write("\n".join([
            "template: t.html",
            "---"
        ]))

        s_gen = SiteGenerator(str(content), config)
        output = tmpdir.mkdir("output")
        s_gen.gen_site(str(output))

        with_title_output = output.join("with-title", "index.html")
        without_title_output = output.join("without-a-title", "index.html")
        child_output = output.join("with-title", "child", "index.html")
        # check the output files exist in the correct place
        assert with_title_output.check()
        assert without_title_output.check()
        assert child_output.check()

        assert with_title_output.read() == "custom title"
        assert without_title_output.read() == "Without a title"

        # Check that custom title is used in breadcrumbs
        exp_bc = ", ".join([HomePage.title, "custom title",
                            "woohoo"])
        assert child_output.read() == exp_bc

    def test_read_context_only(self, tmpdir):
        p = tmpdir.join("mypage.md")
        p.write("\n".join([
            "title: something",
            "---",
            "content goes here"
        ]))
        page = Page("mypage", str(p))
        context, content = page.read_page_source(context_only=True)
        assert context == {"title": "something"}
        assert content == ""

    def test_child_listing(self, site_setup):
        templates, content, output, s_gen = site_setup
        templates.join("c.html").write("\n".join([
            "<ul>",
            "{% for c in children recursive %}",
                "<li>{{ c.path}}, {{ c.title }}</li>",
                "{% if c.children %}",
                    "<ul>",
                    "{{ loop(c.children) }}",
                    "</ul>",
                "{% endif %}",
            "{% endfor %}"
            "</ul>",
        ]))

        files = [
            "a/b/c/page1/index.md",
            "a/b/page2.md",
            "a2/b2/page3.md"
        ]

        for i, f in enumerate(files):
            p = content.join(f)
            if not local(p.dirname).check():
                os.makedirs(p.dirname)
            s = "title: The first page" if i == 0 else ""
            p.write("---\n" + s)

        s_gen.config["default_template"] = "c.html"
        s_gen.gen_site(str(output))

        remove_empties = lambda l: list(filter(None, map(str.strip, l)))

        # root should be all pages
        root = output.join("index.html")
        assert root.check()
        assert remove_empties(root.readlines()) == [
            "<ul>",
                "<li>/a/, A</li>",
                "<ul>",
                    "<li>/a/b/, B</li>",
                    "<ul>",
                        "<li>/a/b/c/, C</li>",
                        "<ul>",
                            "<li>/a/b/c/page1/, Page1</li>",
                        "</ul>",
                        "<li>/a/b/page2/, Page2</li>",
                    "</ul>",
                "</ul>",
                "<li>/a2/, A2</li>",
                "<ul>",
                    "<li>/a2/b2/, B2</li>",
                    "<ul>",
                        "<li>/a2/b2/page3/, Page3</li>",
                    "</ul>",
                "</ul>",
            "</ul>"
        ]

        # inner pages should work too
        inner = output.join("a/b/index.html")
        assert inner.check()
        assert remove_empties(inner.readlines()) == [
            "<ul>",
                "<li>/a/b/c/, C</li>",
                "<ul>",
                    "<li>/a/b/c/page1/, Page1</li>",
                "</ul>",
                "<li>/a/b/page2/, Page2</li>",
            "</ul>",
        ]


class TestConfigs(object):
    def test_basic(self):
        class MyConfig(SiteConfig):
            options = [
                ConfigOption("optional", "hello"),
                ConfigOption("required", None)
            ]

        # missing required value
        with pytest.raises(ValueError):
            MyConfig({"hello": 4})

        got1 = MyConfig({"required": 4}).items()
        assert got1 == {"required": 4, "optional": "hello"}.items()

        got2 = MyConfig({"required": 4, "optional": "goodbye"}).items()
        assert got2 == {"required": 4, "optional": "goodbye"}.items()

    def test_error_on_extra(self):
        opts = [ConfigOption("opt", 4)]

        class ShouldError(SiteConfig):
            options = opts
            error_if_extra = True

        class ShouldNotError(SiteConfig):
            options = opts
            error_if_extra = False

        with pytest.raises(ValueError):
            ShouldError({"extra": 5})

        got = ShouldNotError({"extra": 5}).items()
        expected = {"extra": 5, "opt": 4}.items()
        assert got == expected


class TestMacros(object):
    def test_macros(self, tmpdir):
        templates = tmpdir.mkdir("templates")
        templates.join("c.html").write("{{ content }}")

        content = tmpdir.mkdir("content")
        content.join("index.md").write("\n".join([
            "macros: |",
            "    def simplemacro(s):",
            "        return s.upper()",
            "    def withkwargs(s, **kwargs):",
            "        return repr(kwargs)",
            "---",
            "Macros are <?simplemacro>good<?/simplemacro>",
            "They can span",
            "<?simplemacro>",
            "multiple lines",
            "<?/simplemacro>",
            "",
            "<?withkwargs name=joe job='software dev' age=\"21\">blah<?/withkwargs>"
        ]))

        config = SiteConfig(templates_path=[str(templates)],
                            default_template="c.html")
        s_gen = SiteGenerator(str(content), config)
        output = tmpdir.mkdir("output")
        s_gen.gen_site(str(output))

        html = output.join("index.html")
        assert html.check()
        contents = html.read()

        assert "Macros are GOOD" in contents
        assert "MULTIPLE LINES" in contents
        exp_repr = repr({"name": "joe", "job": "software dev", "age": "21"})
        assert exp_repr in contents


class TestCachedPropertyDecorator(object):
    def test_cached_prop_decorator(self):
        class MyClass:
            def __init__(self):
                self.x = 0

            @cachedproperty
            def myprop(self):
                self.x += 10
                return self.x

        obj = MyClass()
        assert obj.myprop == 10
        assert obj.myprop == 10
        assert obj.myprop == 10
