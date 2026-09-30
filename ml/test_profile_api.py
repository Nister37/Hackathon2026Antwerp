"""Fast contract checks for the deployable two-profile batch artifact."""

from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from ml import ml_study, profile_api


class ProfileArtifactTests(unittest.TestCase):
    def test_batch_output_is_deterministic_and_bound_to_both_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with patch.dict("os.environ", {"ML_PROFILE_DIR": str(output)}):
                with redirect_stdout(StringIO()):
                    profile_api.main()
                    first = (output / "profile_suggestions.json").read_bytes()
                    profile_api.main()
                    second = (output / "profile_suggestions.json").read_bytes()

            self.assertEqual(first, second)
            artifact = json.loads(first)
            self.assertEqual(artifact["schema_version"], 1)
            self.assertEqual(
                {card["customer_id"] for card in artifact["suggestions"]},
                {"TOM", "MARIA"},
            )
            self.assertEqual(len(artifact["suggestions"]), 2)
            for filename in ml_study.SOURCE_FILES.values():
                expected = sha256((ml_study.DATA_DIR / filename).read_bytes()).hexdigest()
                self.assertEqual(artifact["source_sha256"][filename], expected)

    def test_changed_csv_changes_digest_and_duplicate_profile_is_rejected(self) -> None:
        suggestions = [{"customer_id": "TOM"}, {"customer_id": "MARIA"}]
        original = ml_study.profile_artifact(suggestions)
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            for filename in ml_study.SOURCE_FILES.values():
                shutil.copyfile(ml_study.DATA_DIR / filename, data / filename)
            target = data / ml_study.SOURCE_FILES["TOM"]
            target.write_bytes(target.read_bytes() + b"\n")
            with patch.object(ml_study, "DATA_DIR", data):
                changed = ml_study.profile_artifact(suggestions)
            self.assertNotEqual(
                original["source_sha256"][target.name],
                changed["source_sha256"][target.name],
            )
            self.assertEqual(
                original["source_sha256"][ml_study.SOURCE_FILES["MARIA"]],
                changed["source_sha256"][ml_study.SOURCE_FILES["MARIA"]],
            )

        with self.assertRaisesRegex(ValueError, "one suggestion for each"):
            ml_study.profile_artifact(
                [{"customer_id": "TOM"}, {"customer_id": "TOM"}]
            )


if __name__ == "__main__":
    unittest.main()
