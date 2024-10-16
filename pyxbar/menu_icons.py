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
        return self.base64_encode()

    @property
    def image(self) -> str:
        return self.png

    @property
    def png(self) -> Path:
        if not (f := self.cache_dir / f"{self.name}.png").exists():
            self.fetch(f)
        return f

    def fetch(self, f: Path) -> None:
        raise NotImplementedError()

    def resize(self, size: int = 0) -> Path:
        try:
            return self.png_crush(size)
        except FileNotFoundError:
            pass

        return self.sips(size)

    def base64_encode(self, size: int = 0) -> str:
        return (
            (
                base64.encodebytes(self.resize(size or self.size).read_bytes())
                .decode()
                .replace("\n", "")
            )
            if self.image.exists()
            else ""
        )

    def sips(self, size: int = 0, dpi: int = 72, ext: str = "png") -> None:
        size = size or self.size

        if not (f := self.cache_dir / f"{self.name}.{size}.{dpi}dpi.{ext}").exists():
            subprocess.run(
                f"sips -Z {size} -s formatOptions high -s dpiWidth {dpi} -s dpiHeight {dpi} {self.img} --out {f}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return f

    def png_crush(self, size: int = 0) -> Path:
        size = size or self.size
        pngcrush = "/Applications/Xcode.app/Contents/Developer/usr/bin/pngcrush"

        if not Path(pngcrush).exists():
            raise FileNotFoundError(f"{pngcrush} not found")

        if not (f := self.cache_dir / f"{self.name}.{size}.crush.png").exists():
            subprocess.run(
                f"{pngcrush} -brute {self.resize(size)} {f}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return f


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
