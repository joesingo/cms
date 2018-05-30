import time
import os

import yaml
import pytest

from mdss.site_gen import SiteGenerator
from mdss.tree import SiteTree
from mdss.config import SiteConfig, ConfigOption
from mdss.page import Page, PageInfo
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
        templates.join("b.html").write("{{ breadcrumbs }}")

        # Map src path to either list of breadcrumbs OR a tuple
        # (breadcrumbs, dest path)
        home = SiteTree.HOME_PAGE_TITLE
        tests = {
            # home page
            "index.md": [home],
            # single file -- no index.md
            "books.md": ([home, "books"], "books/index.html"),
            # explicit index.md
            "music/index.md": [home, "music"],
            # deeper nesting
            "music/guitar.md": ([home, "music", "guitar"],
                                "music/guitar/index.html"),
            "music/piano/index.md": [home, "music", "piano"],
            "music/piano/chopin.md": ([home, "music", "piano", "chopin"],
                                      "music/piano/chopin/index.html")
        }
        content = tmpdir.mkdir("content")
        for path in tests:
            dirname = os.path.join(str(content), os.path.dirname(path))
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            content.join(path).write("template: b.html")

        config = SiteConfig(templates_path=[str(templates)])
        s_gen = SiteGenerator(str(content), config=config)

        output = tmpdir.mkdir("output")
        s_gen.gen_site(str(output))

        for src_path, val in tests.items():
            if isinstance(val, tuple):
                bc_ids, dest_path = val
            else:
                bc_ids = val
                dest_path = src_path.replace("md", "html")

            with open(os.path.join(str(output), dest_path)) as f:
                contents = f.read().strip()

            bc = [PageInfo(id=p_id, title=Page.get_default_title(p_id))
                  for p_id in bc_ids]
            assert contents == repr(bc)

    def test_split_path(self):
        def t(p): return SiteGenerator.split_path(p)
        assert t("/one/two/three/four.md") == ["one", "two", "three",
                                               "four.md"]
        assert t("/one/two/three/") == ["one", "two", "three"]
        assert t("relative/path/to/file.html") == ["relative", "path", "to",
                                                   "file.html"]
        assert t("relative/dir/") == ["relative", "dir"]


class TestPageRendering(object):
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
            pages.append(Page(name, src_path=str(tmp_file)))

        templates = tmpdir.mkdir("templates")
        templates.join("t.html").write("hello")
        config = SiteConfig(default_template="t.html",
                            templates_path=[str(templates)])

        s_gen = SiteGenerator(content_dir=None, config=config)

        for page in pages:
            with pytest.raises(InvalidPageError):
                s_gen.render_page(page)

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
        exp_bc = ", ".join([SiteTree.HOME_PAGE_TITLE, "custom title",
                            "woohoo"])
        assert child_output.read() == exp_bc


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
