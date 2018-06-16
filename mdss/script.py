import sys
import argparse

from mdss.config import SiteConfig
from mdss.site_gen import SiteGenerator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "export_dir",
        help="The directory to export HTML files to"
    )
    parser.add_argument(
        "-f", "--config-file",
        dest="config_file",
        help="Path to site-wide config file"
    )

    args = parser.parse_args(sys.argv[1:])

    config_path = args.config_file or SiteConfig.find_site_config()
    config = SiteConfig(config_path)
    SiteGenerator(config).gen_site(args.export_dir)


if __name__ == "__main__":
    main()
