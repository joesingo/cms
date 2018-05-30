import os.path
from collections import namedtuple


ConfigOption = namedtuple("ConfigOption", ["name", "default"])


class SiteConfig(dict):
    """
    Class to represent a global site configuration
    """
    options = [
        ConfigOption("templates_path", ["templates"]),
        ConfigOption("default_template", "base.html"),
    ]
    error_if_extra = True

    # filename to look for when searching for site config
    config_filename = "mdss_config.yml"

    def __init__(self, d=None, **kwargs):
        """
        Initialise this config from another dictionary and validate items
        """
        super().__init__()

        d = d or {}
        if kwargs:
            d.update(kwargs)

        for opt in self.options:
            if opt.name in d:
                self[opt.name] = d.pop(opt.name)
            elif opt.default is not None:
                self[opt.name] = opt.default
            else:
                raise ValueError(
                    "Required value '{}' missing".format(opt.name)
                )

        if not self.error_if_extra:
            self.update(d)
        elif d:
            raise ValueError(
                "Unrecognised options: {}".format(", ".join(d.keys()))
            )

    def __getattr__(self, x):
        return self[x]

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
