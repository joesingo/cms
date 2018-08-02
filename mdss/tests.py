import time
import os

import yaml
import pytest
from py.path import local

from mdss.site_gen import SiteGenerator
from mdss.tree import SiteTree
from mdss.config import BaseConfig, SiteConfig, ConfigOption
from mdss.page import Page, HomePage, PageInfo, cachedproperty
from mdss.exceptions import InvalidPageError, NoContentError

class BaseTest:
    @pytest.fixture
    def site_setup(self, tmpdir):
        """
        Provide py.path.local objects for content, template and export dirs,
        and a SiteGenerator object
        """
        templates = tmpdir.mkdir("templates")
        templates.join("def.html").write("{{ content }}")

        content = tmpdir.mkdir("content")
        output = tmpdir.mkdir("output")
        config_dict = {
            "theme_dir": str(templates),
            "default_template": "def.html",
            "content": str(content)
        }
        config_file = tmpdir.join("config.yml")
        config_file.write(yaml.dump(config_dict))
        config = SiteConfig(str(config_file))
        s_gen = SiteGenerator(config)
        return templates, content, output, s_gen

    def create_config(self, tmpdir, cls=SiteConfig, **kwargs):
        f = tmpdir.join("config.yml")
        f.write(yaml.dump(kwargs))
        return cls(str(f))


class TestSiteGeneration(BaseTest):

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

        config = self.create_config(tmpdir, theme_dir=str(templates),
                                    default_template="t.html",
                                    content=str(content))
        s = SiteGenerator(config)
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

    def test_no_content(self, site_setup):
        templates, content, output, s_gen = site_setup
        with pytest.raises(NoContentError):
            s_gen.gen_site(str(output))

    def test_current_page_path(self, site_setup):
        templates, content, output, s_gen = site_setup
        templates.join("t.html").write("{{ path }}")
        s_gen.config["default_template"] = "t.html"

        content.mkdir("one").join("two.md").write("")
        s_gen.gen_site(str(output))

        home = output.join("index.html")
        one = output.join("one", "index.html")
        two = output.join("one", "two", "index.html")
        assert home.check()
        assert one.check()
        assert two.check()

        assert home.read() == "/"
        assert one.read() == "/one/"
        assert two.read() == "/one/two/"

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

        config = self.create_config(tmpdir, theme_dir=str(templates),
                                    default_template="b.html",
                                    content=str(content))
        s_gen = SiteGenerator(config)

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

    def test_default_context(self, site_setup):
        templates, content, output, s_gen = site_setup
        templates.join("d.html").write("{{ the_ultimate_answer }}")
        s_gen.config["default_template"] = "d.html"

        content.join("use-default.md").write("")
        content.join("override.md").write("the_ultimate_answer: 15")

        use_def_output = output.join("use-default/index.html")
        override_output = output.join("override/index.html")

        # without default context set
        s_gen.gen_site(str(output))
        assert use_def_output.read() == ""
        assert override_output.read() == "15"

        # with default context set
        s_gen.config["default_context"] = {"the_ultimate_answer": 42}
        s_gen.gen_site(str(output))
        assert use_def_output.read() == "42"
        assert override_output.read() == "15"

    def test_split_path(self):
        def t(p): return SiteGenerator.split_path(p)
        assert t("/one/two/three/four.md") == ["one", "two", "three",
                                               "four.md"]
        assert t("/one/two/three/") == ["one", "two", "three"]
        assert t("relative/path/to/file.html") == ["relative", "path", "to",
                                                   "file.html"]
        assert t("relative/dir/") == ["relative", "dir"]


class TestStaticFiles(BaseTest):
    def test_static(self, site_setup):
        templates, content, output, s_gen = site_setup

        # static files in template dir
        t1 = templates.mkdir("t1")
        t1.join("style.css").write("t1 file")
        # static file in a subdirectory
        subdir = t1.mkdir("subdir")
        subdir.join("script.js").write("script")
        subdir.join("image.bmp").write("")

        # static files in content dir
        content.mkdir("static").mkdir("css").join("page.css").write("")
        # create files that should be excluded
        content.join("somefile.py").write("")
        content.join("content.md").write("")

        # overwrite same file
        t1.join("double.css").write("t1 version")
        content.join("double.css").write("content version")

        s_gen.config.theme_dir = str(t1)
        s_gen.config.static_filenames = ["css", "js", "bmp"]
        s_gen.gen_site(str(output))

        style_css = output.join("style.css")
        assert style_css.check()
        assert style_css.read() == "t1 file"

        script_js = output.join("subdir", "script.js")
        assert script_js.check()
        image_bmp = output.join("subdir", "image.bmp")
        assert image_bmp.check()

        content_css = output.join("static", "css", "page.css")
        assert content_css.check()

        excluded_file_1 = output.join("somefile.py")
        excluded_file_2 = output.join("content.md")
        assert not excluded_file_1.check()
        assert not excluded_file_2.check()

        double_file = output.join("double.css")
        assert double_file.check()
        assert double_file.read() == "content version"


class TestPageRendering(BaseTest):

    def create_test_page(self, tmpdir, page_id="test", contents_str=None,
                         context={}, content=None):
        tmp_file = tmpdir.join("test_page_{}.md".format(time.time()))

        if not contents_str:
            contents_str = yaml.dump(context)
            contents_str += os.linesep + Page.section_separator + os.linesep
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

        config = self.create_config(tmpdir, theme_dir=str(templates),
                                    default_template="t123.html",
                                    content=str(content))
        s_gen = SiteGenerator(config)

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
            ],
            "invalid-yaml2": [
                "title: blah",
                "template: t.html",
                "something:",
                "   {",
                " - one",
                " - two",
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
        config = self.create_config(tmpdir, default_template="t.html",
                                    theme_dir=str(templates),
                                    content="")

        page = self.create_test_page(tmpdir,
                                     content="This should be **Markdown**")
        s_gen = SiteGenerator(config)
        expected_html = "<p>This should be <strong>Markdown</strong></p>"
        assert s_gen.render_page(page) == expected_html

    def test_title_handling(self, site_setup):
        """
        Check that a title is generated based on filename if title not
        specified in page context.

        Check that if a title is specified it is used in breadcrumbs
        """
        templates, content, output, s_gen = site_setup

        templates.join("t.html").write("{{ title }}")
        templates.join("b.html").write(
            "{{ breadcrumbs|map(attribute='title')|join(', ') }}"
        )

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

        s_gen.config["default_template"] = "t.html"
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

    def test_sitemap(self, site_setup):
        # use the same setup as for child listing test above
        templates, content, output, s_gen = site_setup
        templates.join("p.html").write("\n".join([
            "<ul>",
            "{% for p in sitemap recursive %}",
                "<li>{{ p.path}}, {{ p.title }}</li>",
                "{% if p.children %}",
                    "<ul>",
                    "{{ loop(p.children) }}",
                    "</ul>",
                "{% endif %}",
            "{% endfor %}"
            "</ul>",
        ]))

        files = [
            "foo/bar/baz.md",
            "foo/bar2/aaaa.md"
        ]

        for i, f in enumerate(files):
            p = content.join(f)
            if not local(p.dirname).check():
                os.makedirs(p.dirname)
            p.write("")

        s_gen.config["default_template"] = "p.html"
        s_gen.gen_site(str(output))

        remove_empties = lambda l: list(filter(None, map(str.strip, l)))
        bar2 = output.join("foo", "bar2", "index.html")
        assert bar2.check()
        assert remove_empties(bar2.readlines()) == [
            "<ul>",
                "<li>/foo/, Foo</li>",
                "<ul>",
                    "<li>/foo/bar/, Bar</li>",
                    "<ul>",
                        "<li>/foo/bar/baz/, Baz</li>",
                    "</ul>",
                    "<li>/foo/bar2/, Bar2</li>",
                    "<ul>",
                        "<li>/foo/bar2/aaaa/, Aaaa</li>",
                    "</ul>",
                "</ul>",
            "</ul>"
        ]



class TestConfigs(BaseTest):
    def test_basic(self, tmpdir):
        class MyConfig(BaseConfig):
            options = [
                ConfigOption("optional", "hello"),
                ConfigOption("required", None)
            ]

        # missing required value
        with pytest.raises(ValueError):
            self.create_config(tmpdir, cls=MyConfig, hello=4)

        got1 = self.create_config(tmpdir, cls=MyConfig, required=4).items()
        assert got1 == {"required": 4, "optional": "hello"}.items()

        got2 = self.create_config(tmpdir, cls=MyConfig, required=4,
                                  optional="goodbye").items()
        assert got2 == {"required": 4, "optional": "goodbye"}.items()

    def test_error_on_extra(self, tmpdir):
        opts = [ConfigOption("opt", 4)]

        class ShouldError(BaseConfig):
            options = opts
            error_if_extra = True

        class ShouldNotError(BaseConfig):
            options = opts
            error_if_extra = False

        with pytest.raises(ValueError):
            self.create_config(tmpdir, cls=ShouldError, extra=5)

        got = self.create_config(tmpdir, cls=ShouldNotError, extra=5).items()
        expected = {"extra": 5, "opt": 4}.items()
        assert got == expected

    def test_searching(self, tmpdir):
        one = tmpdir.mkdir("one")
        two = one.mkdir("two")
        three = two.mkdir("three")
        cfg = two.join(SiteConfig.config_filename)
        cfg.write("")

        assert SiteConfig.find_site_config(str(two)) == str(cfg)
        assert SiteConfig.find_site_config(str(three)) == str(cfg)
        with pytest.raises(ValueError):
            SiteConfig.find_site_config(str(one))

    def test_processing(self, tmpdir):
        class ProcessedConfig(BaseConfig):
            options = [
                ConfigOption("x", "hello"),
                ConfigOption("y", None)
            ]

            def process_x(self, s):
                return s[0]

            def process_y(self, s):
                return s.upper()

        cfg1 = self.create_config(tmpdir, cls=ProcessedConfig, y="elephant")
        assert cfg1.x == "h"
        assert cfg1.y == "ELEPHANT"

        cfg2 = self.create_config(tmpdir, cls=ProcessedConfig, x="greetings",
                                  y="lion")
        assert cfg2.x == "g"
        assert cfg2.y == "LION"

    def test_find_content_dir(self, tmpdir):
        """
        Test that content directory defaults to directory containing config
        """
        cfg1 = self.create_config(tmpdir, cls=SiteConfig,
                                  content="/some/content/dir/",
                                  theme_dir="/blah/")
        assert cfg1.content == "/some/content/dir/"

        cfg2_file = tmpdir.join("second_content.yml")
        cfg2_file.write(yaml.dump({"theme_dir": "/blah/"}))
        cfg2 = SiteConfig(str(cfg2_file))
        assert cfg2.content == cfg2_file.dirname


class TestMacros(BaseTest):
    def test_macros(self, tmpdir):
        templates = tmpdir.mkdir("templates")
        templates.join("c.html").write("{{ content }}")

        content = tmpdir.mkdir("content")
        content.join("index.md").write("\n".join([
            "macros: |",
            "    def simplemacro(s):",
            "        return s.upper()",
            "    def withkwargs(s, **kwargs):",
            "        return repr(sorted(kwargs.items()))",
            "---",
            "Macros are <?simplemacro>good<?/simplemacro>",
            "They can span",
            "<?simplemacro>",
            "multiple lines",
            "<?/simplemacro>",
            "",
            "<?withkwargs name=joe job='software dev' age=\"21\">blah<?/withkwargs>"
        ]))

        config = self.create_config(tmpdir, theme_dir=str(templates),
                                    default_template="c.html",
                                    content=str(content))
        s_gen = SiteGenerator(config)
        output = tmpdir.mkdir("output")
        s_gen.gen_site(str(output))

        html = output.join("index.html")
        assert html.check()
        contents = html.read()

        assert "Macros are GOOD" in contents
        assert "MULTIPLE LINES" in contents
        exp_repr = repr([("age", "21"), ("job", "software dev"), ("name", "joe")])
        assert exp_repr in contents

    def test_invalid_name(self, tmpdir):
        templates = tmpdir.mkdir("templates")
        templates.join("c.html").write("{{ content }}")

        content = tmpdir.mkdir("content")
        content.join("index.md").write("\n".join([
            "macros: |",
            "   def misnamed_macro(s):",
            "       return s",
            "---",
            "<?mymacro>hello<?/mymacro>"
        ]))

        config = self.create_config(tmpdir, theme_dir=str(templates),
                                    default_template="c.html",
                                    content=str(content))
        s_gen = SiteGenerator(config)
        output = tmpdir.mkdir("output")
        with pytest.raises(KeyError):
            s_gen.gen_site(str(output))


class TestCachedPropertyDecorator(BaseTest):
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


class TestPageOrdering(BaseTest):
    """
    Tests around the 'page_ordering' property
    """
    def get_order(self, site_setup, ordering=None):
        templates, content, output, s_gen = site_setup
        templates.join("c.html").write(
            "{{ ', '.join(children|map(attribute='title')) }}"
        )
        s_gen.config["default_template"] = "c.html"

        # create content
        content.join("aardvarks.md").write("")
        content.join("snakes.md").write("")
        content.join("turtles.md").write("\n".join((
            "title: A story about turtles",
            "---"
        )))
        content.join("zebras.md").write("")
        content.mkdir("cats").join("index.md").write("")
        content.mkdir("dogs").join("huskies.md").write("")

        # set page ordering
        if ordering:
            print("writing index")
            content.join("index.md").write(yaml.dump({
                "page_ordering": ordering
            }))

        # generate site and return actual ordering
        s_gen.gen_site(str(output))
        return output.join("index.html").read().split(", ")

    def test_default_ordering(self, site_setup):
        # pages should be listed alphabetically by title (not ID) if no
        # ordering given
        assert self.get_order(site_setup) == [
            "A story about turtles", "Aardvarks", "Cats", "Dogs", "Snakes",
            "Zebras"
        ]

    def test_custom_ordering(self, site_setup):
        order = [
            "dogs",
            "cats.md",
            "snakes",
            "turtles",
            "aardvarks",
            "zebras.md"
        ]
        assert self.get_order(site_setup, order) == [
            "Dogs", "Cats", "Snakes", "A story about turtles", "Aardvarks",
            "Zebras"
        ]

    def test_partial_order(self, site_setup):
        # specify only 2 pages in ordering -- the rest should be included in
        # alphabetical order by title at the end
        order = self.get_order(site_setup, ["zebras.md", "dogs", "snakes"])
        assert order == [
            "Zebras", "Dogs", "Snakes", "A story about turtles", "Aardvarks",
            "Cats"
        ]
