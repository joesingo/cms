import os.path
from collections import namedtuple

import yaml


ConfigOption = namedtuple("ConfigOption", ["name", "default"])


class BaseConfig(dict):
    """
    Base config object to handle validation and default values
    """
    options = []
    error_if_extra = True

    def __init__(self, path):
        """
        Initialise this config from another dictionary and validate items.
        """
        super().__init__()

        self.path = path
        with open(self.path) as f:
            d = yaml.load(f) or {}

        for opt in self.options:
            if opt.name in d:
                value = d.pop(opt.name)
                self[opt.name] = value

            elif opt.default is not None:
                self[opt.name] = opt.default
            else:
                raise ValueError(
                    "Required value '{}' missing".format(opt.name)
                )

            # call post-processing function if one is defined
            func_name = "process_{}".format(opt.name)
            if hasattr(self, func_name):
                self[opt.name] = getattr(self, func_name)(self[opt.name])

        if not self.error_if_extra:
            self.update(d)
        elif d:
            raise ValueError(
                "Unrecognised options: {}".format(", ".join(d.keys()))
            )

    def __getattr__(self, x):
        try:
            return self[x]
        except KeyError:
            raise AttributeError


class SiteConfig(BaseConfig):
    """
    Class to represent a global site configuration
    """
    options = [
        ConfigOption("content", ""),  # default to empty string and override in
                                      # process_content
        ConfigOption("theme_dir", None),
        ConfigOption("default_template", "base.html"),
        ConfigOption("default_context", {}),
        ConfigOption("macros", ""),
        ConfigOption("static_filenames", ["css", "js", "png", "jpg", "gif",
                                          "ico", "wav"]),
    ]
    error_if_extra = True

    # filename to look for when searching for site config
    config_filename = "mdss_config.yml"

    @classmethod
    def find_site_config(cls, directory=None):
        directory = os.path.normpath(directory or os.getcwd())
        path = os.path.join(directory, cls.config_filename)

        if os.path.isfile(path):
            return path

        parent_dir = os.path.normpath(os.path.join(directory, os.path.pardir))
        if parent_dir != directory:
            return cls.find_site_config(parent_dir)
        else:
            err_msg = "Cannot find '{}' file".format(cls.config_filename)
            raise ValueError(err_msg)

    def process_content(self, content_dir):
        """
        If not given, set content dir to the parent directory of the config
        file itself
        """
        if not content_dir:
            return os.path.dirname(self.path)
        return os.path.expanduser(content_dir)

    def process_theme_dir(self, t_path):
        return os.path.expanduser(t_path)
