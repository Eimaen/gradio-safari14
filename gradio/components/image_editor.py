"""gr.Image() component."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Iterable, Literal, Optional, TypedDict, Union, cast

import numpy as np
from gradio_client import utils as client_utils
from gradio_client.documentation import document, set_documentation_group
from PIL import Image as _Image  # using _ to minimize namespace pollution

import gradio.image_utils as image_utils
from gradio import utils
from gradio.components.base import Component
from gradio.data_classes import FileData, GradioModel
from gradio.events import Events

set_documentation_group("component")
_Image.init()  # fixes https://github.com/gradio-app/gradio/issues/2843


class PreprocessData(TypedDict):
    background: Optional[Union[np.ndarray, _Image.Image, str]]
    layers: list[Union[np.ndarray, _Image.Image, str]]
    composite: Optional[Union[np.ndarray, _Image.Image, str]]


class EditorData(GradioModel):
    background: Optional[Union[FileData, str]] = None
    layers: list[FileData] = []
    composite: Optional[FileData] = None


class Eraser:
    def __init__(
        self,
        sizes: list[int] | None = None,
        default_size: int | float | None = 20,
        size_mode: Literal["fixed", "defaults"] = "defaults",
        antialias: bool = True,
    ):
        self.sizes = [5, 10, 20, 40, 70] if sizes is None else sizes
        self.default_size = default_size
        self.size_mode = size_mode
        self.antialias = antialias


class Brush(Eraser):
    def __init__(
        self,
        sizes: list[int] | None = None,
        default_size: int | None = 20,
        size_mode: Literal["fixed", "defaults"] = "defaults",
        colors: list[str | tuple[int, int, int, int]]
        | tuple[int, int, int, int]
        | str
        | None = None,
        default_color: str | tuple[int, int, int, int] | None = "red",
        color_mode: Literal["fixed", "defaults"] = "defaults",
        antialias: bool = True,
    ):
        self.colors = (
            ["red", "green", "blue", "yellow", "black", "white"]
            if colors is None
            else colors
        )
        self.default_color = default_color
        self.color_mode = color_mode
        super().__init__(sizes, default_size, size_mode, antialias)


@document()
class ImageEditor(Component):
    """
    Creates an image component that can be used to upload images (as an input) or display images (as an output).
    Preprocessing: passes the uploaded image as a {numpy.array}, {PIL.Image} or {str} filepath depending on `type`.
    Postprocessing: expects a {numpy.array}, {PIL.Image} or {str} or {pathlib.Path} filepath to an image and displays the image.
    Examples-format: a {str} local filepath or URL to an image.
    Demos: image_mod, image_mod_default_image
    Guides: image-classification-in-pytorch, image-classification-in-tensorflow, image-classification-with-vision-transformers, building-a-pictionary_app, create-your-own-friends-with-a-gan
    """

    EVENTS = [
        Events.clear,
        Events.change,
        Events.select,
        Events.upload,
    ]
    data_model = EditorData

    def __init__(
        self,
        value: str | _Image.Image | np.ndarray | None = None,
        *,
        height: int | None = None,
        width: int | None = None,
        image_mode: Literal[
            "1", "L", "P", "RGB", "RGBA", "CMYK", "YCbCr", "LAB", "HSV", "I", "F"
        ] = "RGB",
        sources: Iterable[Literal["upload", "webcam", "clipboard"]] = (
            "upload",
            "webcam",
            "clipboard",
        ),
        type: Literal["numpy", "pil", "filepath"] = "numpy",
        label: str | None = None,
        every: float | None = None,
        show_label: bool | None = None,
        show_download_button: bool = True,
        container: bool = True,
        scale: int | None = None,
        min_width: int = 160,
        interactive: bool | None = None,
        visible: bool = True,
        elem_id: str | None = None,
        elem_classes: list[str] | str | None = None,
        render: bool = True,
        root_url: str | None = None,
        _skip_init_processing: bool = False,
        mirror_webcam: bool = True,
        show_share_button: bool | None = None,
        _selectable: bool = False,
        data_mode: Literal["image", "pathline"] = "image",
        crop_size: tuple[int | float, int | float] | str | None = None,
        transforms: Iterable[Literal["crop", "rotate"]] = ("crop", "rotate"),
        eraser: Eraser | None = None,
        brush: Brush | None = None,
    ):
        """
        Parameters:
            value: A PIL Image, numpy array, path or URL for the default value that Image component is going to take. If callable, the function will be called whenever the app loads to set the initial value of the component.
            height: Height of the displayed image in pixels.
            width: Width of the displayed image in pixels.
            image_mode: "RGB" if color, or "L" if black and white. See https://pillow.readthedocs.io/en/stable/handbook/concepts.html for other supported image modes and their meaning.
            sources: List of sources for the image. "upload" creates a box where user can drop an image file, "webcam" allows user to take snapshot from their webcam, "clipboard" allows users to paste an image from the clipboard.
            type: The format the image is converted to before being passed into the prediction function. "numpy" converts the image to a numpy array with shape (height, width, 3) and values from 0 to 255, "pil" converts the image to a PIL image object, "filepath" passes a str path to a temporary file containing the image.
            label: The label for this component. Appears above the component and is also used as the header if there are a table of examples for this component. If None and used in a `gr.Interface`, the label will be the name of the parameter this component is assigned to.
            every: If `value` is a callable, run the function 'every' number of seconds while the client connection is open. Has no effect otherwise. Queue must be enabled. The event can be accessed (e.g. to cancel it) via this component's .load_event attribute.
            show_label: if True, will display label.
            show_download_button: If True, will display button to download image.
            container: If True, will place the component in a container - providing some extra padding around the border.
            scale: relative width compared to adjacent Components in a Row. For example, if Component A has scale=2, and Component B has scale=1, A will be twice as wide as B. Should be an integer.
            min_width: minimum pixel width, will wrap if not sufficient screen space to satisfy this value. If a certain scale value results in this Component being narrower than min_width, the min_width parameter will be respected first.
            interactive: if True, will allow users to upload and edit an image; if False, can only be used to display images. If not provided, this is inferred based on whether the component is used as an input or output.
            visible: If False, component will be hidden.
            elem_id: An optional string that is assigned as the id of this component in the HTML DOM. Can be used for targeting CSS styles.
            elem_classes: An optional list of strings that are assigned as the classes of this component in the HTML DOM. Can be used for targeting CSS styles.
            render: If False, component will not render be rendered in the Blocks context. Should be used if the intention is to assign event listeners now but render the component later.
            root_url: The remote URL that of the Gradio app that this component belongs to. Used in `gr.load()`. Should not be set manually.
            mirror_webcam: If True webcam will be mirrored. Default is True.
            show_share_button: If True, will show a share icon in the corner of the component that allows user to share outputs to Hugging Face Spaces Discussions. If False, icon does not appear. If set to None (default behavior), then the icon appears if this Gradio app is launched on Spaces, but not otherwise.
            data_mode: The format to receive data from the component. "image" returns an image, "pathline" returns a list of points and a radius.
            crop_size: The size of the crop box in pixels. If a tuple, the first value is the width and the second value is the height. If a string, the value must be a ratio in the form `width:height` (e.g. "16:9").
            transforms: The transforms tools to make available to users. "crop" allows the user to crop the image, "rotate" allows the user to rotate the image.
        """
        self._selectable = _selectable
        self.mirror_webcam = mirror_webcam
        valid_types = ["numpy", "pil", "filepath"]
        if type not in valid_types:
            raise ValueError(
                f"Invalid value for parameter `type`: {type}. Please choose from one of: {valid_types}"
            )
        self.type = type
        self.height = height
        self.width = width
        self.image_mode = image_mode
        valid_sources = ["upload", "webcam", "clipboard"]
        if isinstance(sources, str):
            sources = [sources]  # type: ignore
        for source in sources:
            if source not in valid_sources:
                raise ValueError(
                    f"`sources` must a list consisting of elements in {valid_sources}"
                )
        self.sources = sources

        self.show_download_button = show_download_button

        self.show_share_button = (
            (utils.get_space() is not None)
            if show_share_button is None
            else show_share_button
        )

        self.data_mode = data_mode
        self.crop_size = crop_size
        self.transforms = transforms
        self.eraser = Eraser() if eraser is None else eraser
        self.brush = Brush() if brush is None else brush

        super().__init__(
            label=label,
            every=every,
            show_label=show_label,
            container=container,
            scale=scale,
            min_width=min_width,
            interactive=interactive,
            visible=visible,
            elem_id=elem_id,
            elem_classes=elem_classes,
            render=render,
            root_url=root_url,
            _skip_init_processing=_skip_init_processing,
            value=value,
        )

    def convert_and_format_image(
        self, file: dict | None
    ) -> np.ndarray | _Image.Image | str | None:
        if file is None:
            return None
        im = _Image.open(file["path"])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            im = im.convert(self.image_mode)
        return image_utils.format_image(
            im, cast(Literal["numpy", "pil", "filepath"], self.type), self.GRADIO_CACHE
        )

    def preprocess(self, x: dict | None) -> PreprocessData | None:
        """
        Parameters:
            x: FileData containing an image path pointing to the user's image
        Returns:
            image in requested format, or (if tool == "sketch") a dict of image and mask in requested format
        """
        if x is None:
            return x

        bg = self.convert_and_format_image(x["background"])
        layers = (
            [self.convert_and_format_image(layer) for layer in x["layers"]]
            if x["layers"]
            else None
        )
        composite = self.convert_and_format_image(x["composite"])
        return {
            "background": bg,
            "layers": [x for x in layers if x is not None] if layers else [],
            "composite": composite,
        }

    def postprocess(self, y: PreprocessData | None) -> EditorData | None:
        """
        Parameters:
            y: image as a numpy array, PIL Image, string/Path filepath, or string URL
        Returns:
            base64 url data
        """
        if y is None:
            return None

        layers = (
            [
                FileData(
                    path=image_utils.save_image(
                        cast(np.ndarray | _Image.Image | str, layer),
                        self.GRADIO_CACHE,
                    )
                )
                for layer in y["layers"]
            ]
            if y["layers"]
            else []
        )

        return EditorData(
            background=FileData(
                path=image_utils.save_image(y["background"], self.GRADIO_CACHE)
            )
            if y["background"] is not None
            else None,
            layers=layers,
            composite=FileData(
                path=image_utils.save_image(
                    cast(np.ndarray | _Image.Image | str, y["composite"]),
                    self.GRADIO_CACHE,
                )
            )
            if y["composite"] is not None
            else None,
        )

    def as_example(self, input_data: str | Path | None) -> str:
        if input_data is None:
            return ""
        input_data = str(input_data)
        # If an externally hosted image or a URL, don't convert to absolute path
        if self.root_url or client_utils.is_http_url_like(input_data):
            return input_data
        return str(utils.abspath(input_data))

    def example_inputs(self) -> Any:
        return "https://raw.githubusercontent.com/gradio-app/gradio/main/test/test_files/bus.png"