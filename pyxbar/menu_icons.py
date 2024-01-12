import base64
import subprocess
from dataclasses import dataclass, field
from http.client import OK
from pathlib import Path

import requests

from .utils import cache_dir


@dataclass
class Icon:
    name: str
    cache_dir: Path = field(default_factory=cache_dir)
    size: int = 20

    def __str__(self) -> str:
        return self.png_base64()

    @property
    def png(self) -> Path:
        if not (f := self.cache_dir / f"{self.name}.png").exists():
            self.fetch(f)
        return f

    def fetch(self, f: Path) -> None:
        raise NotImplementedError()

    def resize(self, size: int = 0) -> Path:
        size = size or self.size
        if not (f := self.cache_dir / f"{self.name}.{size}.png").exists():
            subprocess.run(
                f"sips -Z {size} {self.png} --out {f}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return f

    def png_crush(self, size: int = 0) -> Path:
        size = size or self.size
        pngcrush = "/Applications/Xcode.app/Contents/Developer/usr/bin/pngcrush"

        if not (f := self.cache_dir / f"{self.name}.{size}.crush.png").exists():
            subprocess.run(
                f"{pngcrush} -brute {self.resize(size)} {f}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return f

    def png_base64(self, size: int = 0) -> str:
        return (
            (
                base64.encodebytes(self.png_crush(size or self.size).read_bytes())
                .decode()
                .replace("\n", "")
            )
            if self.png.exists()
            else ""
        )


@dataclass
class UrlIcon(Icon):
    url: str = ""

    def fetch(self, f: Path):
        response = requests.get(self.url)
        if OK == response.status_code:
            f.write_bytes(response.content)


@dataclass
class ServiceIcon(Icon):
    def fetch(self, f: Path):
        url = f"https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/{self.name}.png"
        response = requests.get(url)
        if OK == response.status_code:
            f.write_bytes(response.content)


@dataclass
class IcnsIcon(Icon):
    icns_size: int = 32

    def fetch(self, f: Path):
        for apps in ["/System/Applications", "/Applications"]:
            if (app := (Path(apps) / f"{self.name}.app")).exists():
                # find icon
                icns = subprocess.check_output(
                    f"/usr/libexec/PlistBuddy  -c 'Print :CFBundleIconFile' {app}/Contents/Info.plist",
                    shell=True,
                    encoding="utf8",
                    stderr=subprocess.DEVNULL,
                ).strip()

                # extract icon
                subprocess.run(
                    f"icns2png --size {self.icns_size} -x {app}/Contents/Resources/{icns}.icns --out {f.parent}",
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                # reanme icon
                (
                    f.parent
                    / f"{icns}_{self.icns_size}x{self.icns_size}x{self.icns_size}.png"
                ).rename(f)
                break
