import sys
import os
import zipfile
import shutil
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLabel, QFileDialog, QMessageBox,
    QProgressBar, QAbstractItemView
)
from PyQt5.QtCore import Qt


class HwpxMerger(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HWPX 파일 합치기")
        self.setMinimumSize(600, 500)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 안내 레이블
        layout.addWidget(QLabel("합칠 HWPX 파일을 추가하세요 (순서대로 합쳐집니다):"))

        # 파일 목록
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.setDragDropMode(QAbstractItemView.InternalMove)
        layout.addWidget(self.file_list)

        # 버튼 행
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("파일 추가")
        btn_remove = QPushButton("선택 삭제")
        btn_up = QPushButton("위로")
        btn_down = QPushButton("아래로")
        btn_clear = QPushButton("전체 삭제")

        btn_add.clicked.connect(self.add_files)
        btn_remove.clicked.connect(self.remove_selected)
        btn_up.clicked.connect(self.move_up)
        btn_down.clicked.connect(self.move_down)
        btn_clear.clicked.connect(self.file_list.clear)

        for btn in [btn_add, btn_remove, btn_up, btn_down, btn_clear]:
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        # 진행바
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # 합치기 버튼
        btn_merge = QPushButton("HWPX 합치기")
        btn_merge.setFixedHeight(45)
        btn_merge.setStyleSheet("font-size: 15px; background-color: #4CAF50; color: white;")
        btn_merge.clicked.connect(self.merge_files)
        layout.addWidget(btn_merge)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "HWPX 파일 선택", "", "HWPX Files (*.hwpx)")
        for f in files:
            self.file_list.addItem(f)

    def remove_selected(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def move_up(self):
        row = self.file_list.currentRow()
        if row > 0:
            item = self.file_list.takeItem(row)
            self.file_list.insertItem(row - 1, item)
            self.file_list.setCurrentRow(row - 1)

    def move_down(self):
        row = self.file_list.currentRow()
        if row < self.file_list.count() - 1:
            item = self.file_list.takeItem(row)
            self.file_list.insertItem(row + 1, item)
            self.file_list.setCurrentRow(row + 1)

    def merge_files(self):
        if self.file_list.count() < 2:
            QMessageBox.warning(self, "경고", "합칠 파일을 2개 이상 추가해주세요.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "저장할 파일명", "merged.hwpx", "HWPX Files (*.hwpx)")
        if not save_path:
            return

        files = [self.file_list.item(i).text() for i in range(self.file_list.count())]

        try:
            self.progress.setVisible(True)
            self.progress.setMaximum(len(files))
            merge_hwpx(files, save_path, progress_callback=lambda v: self.progress.setValue(v))
            QMessageBox.information(self, "완료", f"합치기 완료!\n저장 위치: {save_path}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"오류 발생:\n{e}")
        finally:
            self.progress.setVisible(False)


def merge_hwpx(file_list: list, output_path: str, progress_callback=None):
    """
    여러 hwpx 파일을 순서대로 합칩니다.
    HWPX는 ZIP 구조이며 핵심 본문은 Contents/section0.xml ~ sectionN.xml 입니다.
    """
    import xml.etree.ElementTree as ET

    tmp_dir = Path("_hwpx_tmp")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir()

    try:
        base_dir = tmp_dir / "base"
        # 첫 번째 파일을 베이스로 압축 해제
        with zipfile.ZipFile(file_list[0], 'r') as z:
            z.extractall(base_dir)

        contents_dir = base_dir / "Contents"
        
        # 기존 섹션 파일 목록 파악
        existing_sections = sorted(
            [f for f in contents_dir.glob("section*.xml")],
            key=lambda x: int(''.join(filter(str.isdigit, x.stem)) or 0)
        )
        section_count = len(existing_sections)

        # 나머지 파일들의 섹션을 추가
        for idx, hwpx_file in enumerate(file_list[1:], start=1):
            src_dir = tmp_dir / f"src_{idx}"
            with zipfile.ZipFile(hwpx_file, 'r') as z:
                z.extractall(src_dir)

            src_contents = src_dir / "Contents"
            src_sections = sorted(
                [f for f in src_contents.glob("section*.xml")],
                key=lambda x: int(''.join(filter(str.isdigit, x.stem)) or 0)
            )

            for sec in src_sections:
                new_name = f"section{section_count}.xml"
                shutil.copy(sec, contents_dir / new_name)
                section_count += 1

            if progress_callback:
                progress_callback(idx)

        # Contents/content.hpf (섹션 목록 manifest) 업데이트
        hpf_path = base_dir / "Contents" / "content.hpf"
        if hpf_path.exists():
            update_hpf(hpf_path, section_count)

        # 결과를 새 zip(hwpx)으로 압축
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for file in base_dir.rglob("*"):
                if file.is_file():
                    zout.write(file, file.relative_to(base_dir))

        if progress_callback:
            progress_callback(len(file_list))

    finally:
        shutil.rmtree(tmp_dir)


def update_hpf(hpf_path: Path, section_count: int):
    """content.hpf에 섹션 항목을 추가합니다."""
    ET = __import__('xml.etree.ElementTree', fromlist=['ElementTree'])
    tree = ET.parse(hpf_path)
    root = tree.getroot()
    ns = {'opf': 'http://www.idpf.org/2007/opf'}

    manifest = root.find('.//opf:manifest', ns) or root.find('.//{*}manifest')
    spine = root.find('.//opf:spine', ns) or root.find('.//{*}spine')

    if manifest is None or spine is None:
        return  # hpf 구조가 다르면 스킵

    existing_ids = {item.get('id') for item in manifest}

    for i in range(section_count):
        sec_id = f"section{i}"
        if sec_id not in existing_ids:
            ns_uri = list(root.nsmap.values())[0] if hasattr(root, 'nsmap') else ''
            item = ET.SubElement(manifest, f"item")
            item.set('id', sec_id)
            item.set('href', f"section{i}.xml")
            item.set('media-type', 'application/xml')

            itemref = ET.SubElement(spine, "itemref")
            itemref.set('idref', sec_id)

    tree.write(hpf_path, xml_declaration=True, encoding='UTF-8')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HwpxMerger()
    window.show()
    sys.exit(app.exec_())
