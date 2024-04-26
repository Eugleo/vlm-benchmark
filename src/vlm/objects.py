from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Protocol, Union

import polars as pl
import yaml


@dataclass
class Task:
    id: str
    label_prompts: dict[str, str]

    prompt_gpt: Optional[str]
    prompt_baseline: Optional[str]

    @property
    def labels(self) -> list[str]:
        return list(self.label_prompts.keys())

    @staticmethod
    def from_file(id: str, path: Union[str, Path]) -> "Task":
        with open(path) as f:
            data = yaml.safe_load(f)
        return Task(id=id, **data)


@dataclass
class Video:
    path: str
    labels: dict[str, str]


class Model(Protocol):
    id: str

    def predict(self, videos: list[Video], tasks: list[Task]) -> pl.DataFrame:
        """Predict the probability of each label in each task for each video.
        Returns a DataFrame with the following columns:
        - task: The task ID
        - head: The head ID
        - video: The path to the video
        - label: The label for which the probability is predicted
        - prob: The predicted probability
        - true_prob: The true probability (1.0 if the label is correct, 0.0 otherwise)
        """
        ...


@dataclass
class Experiment:
    id: str
    tasks: list[Task]
    videos: list[Video]
    models: list[Callable[[], Model]]
    config_file: str

    output_dir: str

    def run(self) -> pl.DataFrame:
        output_dir = Path(self.output_dir) / self.id
        output_dir.mkdir(exist_ok=True, parents=True)
        (output_dir / "config.yaml").write_text(Path(self.config_file).read_text())

        results: list[pl.DataFrame] = []
        for get_model in self.models:
            model = get_model()
            print(f"Running model {model.id}")
            result = model.predict(self.videos, self.tasks)
            results.append(result)
        result = pl.concat(results)

        result.write_csv(output_dir / "results.csv")
        return result