from pathlib import Path

from pydicom import config
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import UID, ExplicitVRLittleEndian

from storitch.identify_file import get_dicom_elements


def test_overlong_decimal_strings_do_not_remove_functional_groups(
    tmp_path: Path,
) -> None:
    path = tmp_path / 'multiframe.dcm'
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = UID('1.2.840.10008.5.1.4.1.1.13.1.2')
    file_meta.MediaStorageSOPInstanceUID = UID('1.2.3.4')
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    dataset = FileDataset(path, {}, file_meta=file_meta, preamble=b'\0' * 128)
    dataset.SOPClassUID = file_meta.MediaStorageSOPClassUID
    dataset.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    dataset.NumberOfFrames = 2

    pixel_measures = Dataset()
    plane_position = Dataset()
    with config.disable_value_validation():
        pixel_measures.PixelSpacing = [
            '0.1599999964237213',
            '0.1599999964237213',
        ]
        pixel_measures.SliceThickness = '0.1599999964237213'
        plane_position.ImagePositionPatient = [
            '0',
            '0',
            '102.23999771475792',
        ]

    shared = Dataset()
    shared.PixelMeasuresSequence = Sequence([pixel_measures])
    per_frame = Dataset()
    per_frame.PlanePositionSequence = Sequence([plane_position])
    dataset.SharedFunctionalGroupsSequence = Sequence([shared])
    dataset.PerFrameFunctionalGroupsSequence = Sequence([per_frame, per_frame])
    dataset.PixelData = b'\0\0'
    with config.disable_value_validation():
        dataset.save_as(path, enforce_file_format=True)

    metadata = get_dicom_elements(path)

    assert metadata is not None
    assert metadata['52009229']['Value'][0]['00289110']['Value'][0]['00280030'][
        'Value'
    ] == [0.15999999642372, 0.15999999642372]
    assert len(metadata['52009230']['Value']) == 2
    assert metadata['52009230']['Value'][0]['00209113']['Value'][0]['00200032'][
        'Value'
    ] == [0.0, 0.0, 102.239997714758]
