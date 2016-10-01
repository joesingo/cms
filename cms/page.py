import yaml
import markdown
import os

class Page(object):
    """A class to represent a web page. A page is loaded from a file that
    contains a YAML config section followed by the content as a markdown"""

    # The delimiter between the YAML config section and markdown content
    START_OF_CONTENT = "\n---\n"

    def __init__(self, filename, config=None, config_only=False):
        """Construct a Page object from a given file"""
        self.config = config or {}

        try:
            with open(filename) as f:
                file_contents = f.read()

                # Split the contents of the file into the config and contents
                # sections
                # TODO: Only read up to START_OF_CONTENT if config_only is True
                config_str, contents_str = file_contents.split(Page.START_OF_CONTENT, 1)

        except IOError:
            # If file does not exist then this must be an index page
            config_str, contents_str = "", ""

        this_config = yaml.load(config_str) or {}

        # If base_config has been specified, load and merge the base config
        if "base_config" in this_config:
            base_page = Page(this_config["base_config"], config_only=True)
            self.config = Page.merge_configs(self.config, base_page.config)

        # Set default title here in case it has not been specified in this_config
        self.config["title"] = Page.format_page_name(filename)

        self.config = Page.merge_configs(self.config, this_config)

        # Deal with the contents of the page if we are not only interested in
        # the config
        if not config_only:

            # Replace custom elements with their HTML counterparts
            if "custom_elements" in self.config:
                for custom_el, replacement in self.config["custom_elements"].items():
                    start_tag = "<" + custom_el + ">"
                    end_tag = "</" + custom_el + ">"

                    new_start_tag, new_end_tag = replacement.split("$", 1)

                    contents_str = contents_str.replace(start_tag, new_start_tag)
                    contents_str = contents_str.replace(end_tag, new_end_tag)

            # Convert markdown to HTML
            self.config["content"] = markdown.markdown(contents_str)

            # Set a flag in the config if this is an index page, as the template
            # may want to do something different in this case
            if filename.endswith("index.md"):
                self.config["index_page"] = True

    def to_html(self, env):
        """Return the entire HTML document as a string for this page"""
        template = env.get_template(self.config["template"])
        return template.render(self.config)

    @classmethod
    def format_page_name(cls, file):
        """Given the filename or path to a page, return a nicely formatted
        version by replacing hyphens/underscores with spaces and capitalising
        the first letter"""
        if file.endswith(".md"):
            file = file[:-3]

        if file.endswith("/index"):
            file = file[:-6]

        name = os.path.basename(file)
        name = name.replace("-", " ").capitalize()
        name = name.replace("_", " ").capitalize()
        return name

    @classmethod
    def merge_configs(cls, base, new):
        """Merge the config 'new' into 'base' by appending/overwriting fields
        in 'base' with fields in 'new'"""
        config = base.copy()

        for i in new:
            if i in config:
                # If the value is a list then concatenate the two lists
                if type(new[i]) == list:
                    config[i] += new[i]

                # If the value is a dict then update base to include keys from
                # new
                elif type(new[i]) == dict:
                    config[i].update(new[i])

                # For any other datatype we must overwrite
                else:
                    config[i] = new[i]

            # If the new value does not exist in base config then we must
            # overwrite
            else:
                config[i] = new[i]

        return config