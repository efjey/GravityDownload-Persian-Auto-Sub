from pathlib import Path

from PySide6.QtCore import (
    Qt,
    QThread,
    Signal,
)

from PySide6.QtGui import (
    QFont,
)

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.translator import (
    Translator,
)

from app.utils.config import (
    APP_NAME,
    APP_VERSION,
    OPENAI_MODEL,
    SUPPORTED_LANGUAGES,
    WHISPER_MODELS,
    VIDEO_EXTENSIONS,
    LOGS_DIR,
)

from app.utils.ffmpeg import (
    FFmpegManager,
)

from app.utils.logger import (
    setup_logger,
    create_qt_log_handler,
    get_logger,
)

from app.workers.processing_worker import (
    ProcessingWorker,
)


# ============================================================
# API Test Worker
# ============================================================

class APITestWorker(QThread):

    finished = Signal(bool, str)

    def __init__(
        self,
        api_key,
        model,
        parent=None,
    ):

        super().__init__(
            parent
        )

        self.api_key = api_key
        self.model = model

    def run(self):

        try:

            translator = Translator(
                api_key=self.api_key,
                model=self.model,
            )

            result = translator.test_connection()

            self.finished.emit(
                True,
                result
            )

        except Exception as exc:

            self.finished.emit(
                False,
                str(exc)
            )


# ============================================================
# Main Window
# ============================================================

class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        # ----------------------------------------------------
        # Logger
        # ----------------------------------------------------

        setup_logger(
            LOGS_DIR
        )

        self.logger = get_logger()

        self.qt_log_handler = (
            create_qt_log_handler()
        )

        self.qt_log_handler.message.connect(
            self.append_log
        )

        # ----------------------------------------------------
        # Workers
        # ----------------------------------------------------

        self.api_test_worker = None

        self.processing_worker = None

        # ----------------------------------------------------
        # State
        # ----------------------------------------------------

        self.selected_folder = None

        # ----------------------------------------------------
        # Window
        # ----------------------------------------------------

        self.setWindowTitle(
            APP_NAME
        )

        self.resize(
            950,
            780
        )

        self.setMinimumSize(
            720,
            550
        )

        self._build_ui()

        self._apply_style()

        self.logger.info(
            "برنامه اجرا شد."
        )

    # ========================================================
    # Build UI
    # ========================================================

    def _build_ui(self):

        central = QWidget()

        self.setCentralWidget(
            central
        )

        outer_layout = QVBoxLayout(
            central
        )

        outer_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        # ----------------------------------------------------
        # Scroll
        # ----------------------------------------------------

        self.scroll_area = QScrollArea()

        self.scroll_area.setWidgetResizable(
            True
        )

        self.scroll_area.setFrameShape(
            QFrame.NoFrame
        )

        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        outer_layout.addWidget(
            self.scroll_area
        )

        content = QWidget()

        self.scroll_area.setWidget(
            content
        )

        main_layout = QVBoxLayout(
            content
        )

        main_layout.setContentsMargins(
            28,
            25,
            28,
            30
        )

        main_layout.setSpacing(
            18
        )

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        title = QLabel(
            APP_NAME
        )

        title.setObjectName(
            "title"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        main_layout.addWidget(
            title
        )

        subtitle = QLabel(
            f"Automatic Subtitle Generator • v{APP_VERSION}"
        )

        subtitle.setObjectName(
            "subtitle"
        )

        subtitle.setAlignment(
            Qt.AlignCenter
        )

        main_layout.addWidget(
            subtitle
        )

        # ----------------------------------------------------
        # Folder
        # ----------------------------------------------------

        folder_card = self._create_card()

        folder_layout = QVBoxLayout(
            folder_card
        )

        folder_title = QLabel(
            "📁 انتخاب پوشه ویدیوها"
        )

        folder_title.setObjectName(
            "sectionTitle"
        )

        folder_layout.addWidget(
            folder_title
        )

        folder_row = QHBoxLayout()

        self.folder_label = QLabel(
            "هیچ پوشه‌ای انتخاب نشده است"
        )

        self.folder_label.setObjectName(
            "pathLabel"
        )

        self.folder_label.setWordWrap(
            True
        )

        folder_row.addWidget(
            self.folder_label,
            1
        )

        self.browse_button = QPushButton(
            "انتخاب پوشه"
        )

        self.browse_button.clicked.connect(
            self.select_folder
        )

        folder_row.addWidget(
            self.browse_button
        )

        folder_layout.addLayout(
            folder_row
        )

        main_layout.addWidget(
            folder_card
        )

        # ----------------------------------------------------
        # AI
        # ----------------------------------------------------

        ai_card = self._create_card()

        ai_layout = QVBoxLayout(
            ai_card
        )

        ai_title = QLabel(
            "🤖 تنظیمات هوش مصنوعی"
        )

        ai_title.setObjectName(
            "sectionTitle"
        )

        ai_layout.addWidget(
            ai_title
        )

        api_label = QLabel(
            "OpenAI API Key"
        )

        api_label.setObjectName(
            "fieldLabel"
        )

        ai_layout.addWidget(
            api_label
        )

        api_row = QHBoxLayout()

        self.api_key_input = QLineEdit()

        self.api_key_input.setPlaceholderText(
            "API Key خود را وارد کنید..."
        )

        self.api_key_input.setEchoMode(
            QLineEdit.Password
        )

        self.api_key_input.setClearButtonEnabled(
            True
        )

        api_row.addWidget(
            self.api_key_input,
            1
        )

        self.show_api_button = QPushButton(
            "نمایش"
        )

        self.show_api_button.setCheckable(
            True
        )

        self.show_api_button.setFixedWidth(
            85
        )

        self.show_api_button.toggled.connect(
            self.toggle_api_visibility
        )

        api_row.addWidget(
            self.show_api_button
        )

        ai_layout.addLayout(
            api_row
        )

        security_note = QLabel(
            "🔒 API Key فقط در حافظه برنامه استفاده می‌شود "
            "و در فایل ذخیره نخواهد شد."
        )

        security_note.setObjectName(
            "hint"
        )

        security_note.setWordWrap(
            True
        )

        ai_layout.addWidget(
            security_note
        )

        model_label = QLabel(
            "مدل OpenAI"
        )

        model_label.setObjectName(
            "fieldLabel"
        )

        ai_layout.addWidget(
            model_label
        )

        self.openai_model_combo = QComboBox()

        self.openai_model_combo.addItems(
            [
                "gpt-5-mini",
                "gpt-5.4-mini",
                "gpt-5.4",
            ]
        )

        current_model = (
            self.openai_model_combo.findText(
                OPENAI_MODEL
            )
        )

        if current_model >= 0:

            self.openai_model_combo.setCurrentIndex(
                current_model
            )

        ai_layout.addWidget(
            self.openai_model_combo
        )

        test_row = QHBoxLayout()

        self.api_status_label = QLabel(
            "وضعیت: تست نشده"
        )

        self.api_status_label.setObjectName(
            "status"
        )

        self.test_api_button = QPushButton(
            "تست اتصال API"
        )

        self.test_api_button.clicked.connect(
            self.test_openai_connection
        )

        test_row.addWidget(
            self.api_status_label,
            1
        )

        test_row.addWidget(
            self.test_api_button
        )

        ai_layout.addLayout(
            test_row
        )

        main_layout.addWidget(
            ai_card
        )

        # ----------------------------------------------------
        # Languages
        # ----------------------------------------------------

        language_card = self._create_card()

        language_layout = QVBoxLayout(
            language_card
        )

        language_title = QLabel(
            "🌐 زبان‌ها"
        )

        language_title.setObjectName(
            "sectionTitle"
        )

        language_layout.addWidget(
            language_title
        )

        source_label = QLabel(
            "زبان اصلی ویدیو"
        )

        source_label.setObjectName(
            "fieldLabel"
        )

        language_layout.addWidget(
            source_label
        )

        self.source_language_combo = QComboBox()

        self.source_language_combo.addItems(
            list(
                SUPPORTED_LANGUAGES.keys()
            )
        )

        self.source_language_combo.setCurrentText(
            "Auto Detect"
        )

        language_layout.addWidget(
            self.source_language_combo
        )

        source_hint = QLabel(
            "برای تشخیص خودکار زبان، Auto Detect را انتخاب کنید."
        )

        source_hint.setObjectName(
            "hint"
        )

        source_hint.setWordWrap(
            True
        )

        language_layout.addWidget(
            source_hint
        )

        target_label = QLabel(
            "زبان زیرنویس خروجی"
        )

        target_label.setObjectName(
            "fieldLabel"
        )

        language_layout.addWidget(
            target_label
        )

        self.target_language_combo = QComboBox()

        self.target_language_combo.addItems(
            list(
                SUPPORTED_LANGUAGES.keys()
            )
        )

        self.target_language_combo.setCurrentText(
            "Persian"
        )

        language_layout.addWidget(
            self.target_language_combo
        )

        main_layout.addWidget(
            language_card
        )

        # ----------------------------------------------------
        # Whisper
        # ----------------------------------------------------

        whisper_card = self._create_card()

        whisper_layout = QVBoxLayout(
            whisper_card
        )

        whisper_title = QLabel(
            "🎙️ تشخیص گفتار"
        )

        whisper_title.setObjectName(
            "sectionTitle"
        )

        whisper_layout.addWidget(
            whisper_title
        )

        whisper_label = QLabel(
            "مدل Whisper"
        )

        whisper_label.setObjectName(
            "fieldLabel"
        )

        whisper_layout.addWidget(
            whisper_label
        )

        self.whisper_model_combo = QComboBox()

        self.whisper_model_combo.addItems(
            WHISPER_MODELS
        )

        self.whisper_model_combo.setCurrentText(
            "small"
        )

        whisper_layout.addWidget(
            self.whisper_model_combo
        )

        whisper_hint = QLabel(
            "مدل‌های بزرگ‌تر معمولاً دقت بیشتری دارند، "
            "اما حافظه و زمان بیشتری مصرف می‌کنند."
        )

        whisper_hint.setObjectName(
            "hint"
        )

        whisper_hint.setWordWrap(
            True
        )

        whisper_layout.addWidget(
            whisper_hint
        )

        main_layout.addWidget(
            whisper_card
        )

        # ----------------------------------------------------
        # Videos
        # ----------------------------------------------------

        videos_card = self._create_card()

        videos_layout = QVBoxLayout(
            videos_card
        )

        videos_title = QLabel(
            "🎬 فایل‌های ویدیویی"
        )

        videos_title.setObjectName(
            "sectionTitle"
        )

        videos_layout.addWidget(
            videos_title
        )

        self.video_list = QListWidget()

        self.video_list.setMinimumHeight(
            180
        )

        self.video_list.setMaximumHeight(
            330
        )

        videos_layout.addWidget(
            self.video_list
        )

        main_layout.addWidget(
            videos_card
        )

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        progress_card = self._create_card()

        progress_layout = QVBoxLayout(
            progress_card
        )

        self.progress_label = QLabel(
            "آماده شروع"
        )

        self.progress_label.setObjectName(
            "status"
        )

        progress_layout.addWidget(
            self.progress_label
        )

        self.progress_bar = QProgressBar()

        self.progress_bar.setRange(
            0,
            100
        )

        self.progress_bar.setValue(
            0
        )

        progress_layout.addWidget(
            self.progress_bar
        )

        main_layout.addWidget(
            progress_card
        )

        # ----------------------------------------------------
        # Buttons
        # ----------------------------------------------------

        buttons_row = QHBoxLayout()

        self.start_button = QPushButton(
            "▶ شروع پردازش"
        )

        self.start_button.setObjectName(
            "primaryButton"
        )

        self.start_button.clicked.connect(
            self.start_processing
        )

        self.stop_button = QPushButton(
            "■ توقف"
        )

        self.stop_button.setEnabled(
            False
        )

        self.stop_button.clicked.connect(
            self.stop_processing
        )

        buttons_row.addWidget(
            self.start_button
        )

        buttons_row.addWidget(
            self.stop_button
        )

        main_layout.addLayout(
            buttons_row
        )

        # ----------------------------------------------------
        # Log
        # ----------------------------------------------------

        log_card = self._create_card()

        log_layout = QVBoxLayout(
            log_card
        )

        log_header = QHBoxLayout()

        log_title = QLabel(
            "📋 Log پردازش"
        )

        log_title.setObjectName(
            "sectionTitle"
        )

        self.log_toggle_button = QPushButton(
            "بستن Log"
        )

        self.log_toggle_button.setCheckable(
            True
        )

        self.log_toggle_button.setChecked(
            True
        )

        self.log_toggle_button.clicked.connect(
            self.toggle_log
        )

        self.clear_log_button = QPushButton(
            "پاک کردن"
        )

        self.clear_log_button.clicked.connect(
            self.clear_log
        )

        log_header.addWidget(
            log_title,
            1
        )

        log_header.addWidget(
            self.clear_log_button
        )

        log_header.addWidget(
            self.log_toggle_button
        )

        log_layout.addLayout(
            log_header
        )

        self.log_output = QTextEdit()

        self.log_output.setReadOnly(
            True
        )

        self.log_output.setMinimumHeight(
            180
        )

        self.log_output.setMaximumHeight(
            350
        )

        self.log_output.setPlaceholderText(
            "Log برنامه اینجا نمایش داده می‌شود..."
        )

        log_layout.addWidget(
            self.log_output
        )

        main_layout.addWidget(
            log_card
        )

        self.log_card = log_card

        # ----------------------------------------------------
        # Footer
        # ----------------------------------------------------

        footer = QLabel(
            "GravityDownload Persian Auto Sub"
        )

        footer.setObjectName(
            "footer"
        )

        footer.setAlignment(
            Qt.AlignCenter
        )

        main_layout.addWidget(
            footer
        )

        main_layout.addStretch()

    # ========================================================
    # Card
    # ========================================================

    @staticmethod
    def _create_card():

        card = QFrame()

        card.setObjectName(
            "card"
        )

        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )

        return card

    # ========================================================
    # API Visibility
    # ========================================================

    def toggle_api_visibility(
        self,
        checked
    ):

        if checked:

            self.api_key_input.setEchoMode(
                QLineEdit.Normal
            )

            self.show_api_button.setText(
                "مخفی"
            )

        else:

            self.api_key_input.setEchoMode(
                QLineEdit.Password
            )

            self.show_api_button.setText(
                "نمایش"
            )

    # ========================================================
    # Folder
    # ========================================================

    def select_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "انتخاب پوشه ویدیوها"
        )

        if not folder:
            return

        self.selected_folder = Path(
            folder
        )

        self.folder_label.setText(
            self._shorten_path(
                str(
                    self.selected_folder
                )
            )
        )

        self.folder_label.setToolTip(
            str(
                self.selected_folder
            )
        )

        self.scan_videos()

        self.logger.info(
            f"پوشه انتخاب شد: "
            f"{self.selected_folder}"
        )

    # ========================================================
    # Short Path
    # ========================================================

    @staticmethod
    def _shorten_path(
        path,
        max_length=75
    ):

        if len(path) <= max_length:
            return path

        path_obj = Path(
            path
        )

        parts = path_obj.parts

        if len(parts) <= 2:

            return (
                path[:max_length - 3]
                + "..."
            )

        result = (
            parts[0]
            + "\\...\\"
            + "\\".join(
                parts[-2:]
            )
        )

        if len(result) <= max_length:
            return result

        return (
            result[:max_length - 3]
            + "..."
        )

    # ========================================================
    # Scan
    # ========================================================

    def scan_videos(self):

        self.video_list.clear()

        if not self.selected_folder:
            return

        try:

            videos = [
                file
                for file in self.selected_folder.iterdir()
                if (
                    file.is_file()
                    and file.suffix.lower()
                    in VIDEO_EXTENSIONS
                )
            ]

        except Exception as exc:

            QMessageBox.critical(
                self,
                "خطا",
                f"امکان خواندن پوشه وجود ندارد:\n{exc}"
            )

            return

        videos.sort(
            key=lambda x: x.name.lower()
        )

        for video in videos:

            item = QListWidgetItem(
                video.name
            )

            item.setToolTip(
                str(video)
            )

            self.video_list.addItem(
                item
            )

        self.progress_label.setText(
            f"{len(videos)} فایل ویدیویی پیدا شد."
        )

        self.logger.info(
            f"{len(videos)} فایل ویدیویی پیدا شد."
        )

    # ========================================================
    # API Test
    # ========================================================

    def test_openai_connection(self):

        api_key = (
            self.api_key_input.text()
            .strip()
        )

        if not api_key:

            QMessageBox.warning(
                self,
                "API Key",
                "ابتدا API Key خود را وارد کنید."
            )

            self.api_key_input.setFocus()

            return

        model = (
            self.openai_model_combo.currentText()
        )

        self.test_api_button.setEnabled(
            False
        )

        self.api_status_label.setText(
            "وضعیت: در حال تست..."
        )

        self.logger.info(
            "در حال تست اتصال OpenAI..."
        )

        self.api_test_worker = APITestWorker(
            api_key,
            model,
            self
        )

        self.api_test_worker.finished.connect(
            self._api_test_finished
        )

        self.api_test_worker.start()

    # ========================================================
    # API Result
    # ========================================================

    def _api_test_finished(
        self,
        success,
        message
    ):

        self.test_api_button.setEnabled(
            True
        )

        if success:

            self.api_status_label.setText(
                "وضعیت: ✓ اتصال موفق"
            )

            self.logger.info(
                "اتصال OpenAI موفق بود."
            )

            QMessageBox.information(
                self,
                "موفق",
                "اتصال به OpenAI با موفقیت انجام شد."
            )

        else:

            self.api_status_label.setText(
                "وضعیت: ✕ خطا"
            )

            self.logger.error(
                f"خطای OpenAI: {message}"
            )

            QMessageBox.critical(
                self,
                "خطا",
                message
            )

        if self.api_test_worker:

            self.api_test_worker.deleteLater()

            self.api_test_worker = None

    # ========================================================
    # Start
    # ========================================================

    def start_processing(self):

        if self.processing_worker is not None:

            QMessageBox.warning(
                self,
                "در حال پردازش",
                "یک پردازش در حال اجرا است."
            )

            return

        if not self.selected_folder:

            QMessageBox.warning(
                self,
                "پوشه",
                "ابتدا پوشه ویدیوها را انتخاب کنید."
            )

            return

        # ----------------------------------------------------
        # Collect videos
        # ----------------------------------------------------

        videos = []

        for index in range(
            self.video_list.count()
        ):

            item = self.video_list.item(
                index
            )

            video_path = (
                self.selected_folder
                / item.text()
            )

            if video_path.exists():

                videos.append(
                    video_path
                )

        if not videos:

            QMessageBox.warning(
                self,
                "ویدیو",
                "هیچ فایل ویدیویی پیدا نشد."
            )

            return

        # ----------------------------------------------------
        # API Key
        # ----------------------------------------------------

        api_key = (
            self.api_key_input.text()
            .strip()
        )

        if not api_key:

            QMessageBox.warning(
                self,
                "API Key",
                "ابتدا API Key خود را وارد کنید."
            )

            self.api_key_input.setFocus()

            return

        # ----------------------------------------------------
        # Settings
        # ----------------------------------------------------

        model = (
            self.openai_model_combo.currentText()
        )

        whisper_model = (
            self.whisper_model_combo.currentText()
        )

        source_language = (
            self.source_language_combo.currentText()
        )

        target_language = (
            self.target_language_combo.currentText()
        )

        # ----------------------------------------------------
        # Convert language names to codes
        # ----------------------------------------------------

        source_code = (
            SUPPORTED_LANGUAGES.get(
                source_language
            )
        )

        target_code = (
            SUPPORTED_LANGUAGES.get(
                target_language
            )
        )

        # Auto Detect باید None باشد
        if source_language == "Auto Detect":

            source_code = None

        if target_code is None:

            QMessageBox.warning(
                self,
                "زبان مقصد",
                "زبان مقصد معتبر نیست."
            )

            return

        # ----------------------------------------------------
        # FFmpeg Check
        # ----------------------------------------------------

        ffmpeg = FFmpegManager()

        if not ffmpeg.is_available():

            QMessageBox.critical(
                self,
                "FFmpeg پیدا نشد",
                "FFmpeg پیدا نشد.\n\n"
                "ffmpeg.exe را داخل پوشه ffmpeg پروژه قرار دهید "
                "یا FFmpeg را به PATH ویندوز اضافه کنید."
            )

            self.logger.error(
                "FFmpeg پیدا نشد."
            )

            return

        # ----------------------------------------------------
        # Log
        # ----------------------------------------------------

        self.log_output.clear()

        self.logger.info(
            "================================"
        )

        self.logger.info(
            "شروع پردازش ویدیوها"
        )

        self.logger.info(
            f"تعداد فایل‌ها: {len(videos)}"
        )

        self.logger.info(
            f"Whisper: {whisper_model}"
        )

        self.logger.info(
            f"OpenAI: {model}"
        )

        self.logger.info(
            f"زبان مبدأ: {source_language}"
        )

        self.logger.info(
            f"کد زبان مبدأ: "
            f"{source_code or 'auto'}"
        )

        self.logger.info(
            f"زبان مقصد: {target_language}"
        )

        self.logger.info(
            f"کد زبان مقصد: {target_code}"
        )

        self.logger.info(
            "================================"
        )

        # ----------------------------------------------------
        # UI State
        # ----------------------------------------------------

        self.start_button.setEnabled(
            False
        )

        self.browse_button.setEnabled(
            False
        )

        self.test_api_button.setEnabled(
            False
        )

        self.stop_button.setEnabled(
            True
        )

        self.progress_bar.setValue(
            0
        )

        self.progress_label.setText(
            "در حال پردازش..."
        )

        # ----------------------------------------------------
        # Worker
        # ----------------------------------------------------

        self.processing_worker = ProcessingWorker(
            videos=videos,
            api_key=api_key,
            openai_model=model,
            whisper_model=whisper_model,
            source_language=source_code,
            target_language=target_code,
            parent=self,
        )

        self.processing_worker.progress.connect(
            self.progress_bar.setValue
        )

        self.processing_worker.log.connect(
            self.logger.info
        )

        self.processing_worker.video_started.connect(
            self.on_video_started
        )

        self.processing_worker.video_finished.connect(
            self.on_video_finished
        )

        self.processing_worker.error.connect(
            self.on_processing_error
        )

        self.processing_worker.finished.connect(
            self.on_processing_finished
        )

        self.processing_worker.start()

    # ========================================================
    # Video Started
    # ========================================================

    def on_video_started(
        self,
        video_name
    ):

        self.progress_label.setText(
            f"در حال پردازش: {video_name}"
        )

    # ========================================================
    # Video Finished
    # ========================================================

    def on_video_finished(
        self,
        video_name
    ):

        self.logger.info(
            f"✓ پایان: {video_name}"
        )

    # ========================================================
    # Processing Error
    # ========================================================

    def on_processing_error(
        self,
        message
    ):

        self.logger.error(
            message
        )

    # ========================================================
    # Processing Finished
    # ========================================================

    def on_processing_finished(self):

        worker = self.processing_worker

        self.processing_worker = None

        self.start_button.setEnabled(
            True
        )

        self.browse_button.setEnabled(
            True
        )

        self.test_api_button.setEnabled(
            True
        )

        self.stop_button.setEnabled(
            False
        )

        if self.progress_bar.value() >= 100:

            self.progress_label.setText(
                "✓ پردازش کامل شد."
            )

            QMessageBox.information(
                self,
                "پایان پردازش",
                "پردازش فایل‌ها به پایان رسید."
            )

        else:

            self.progress_label.setText(
                "پردازش متوقف شد."
            )

        if worker:

            worker.deleteLater()

    # ========================================================
    # Stop
    # ========================================================

    def stop_processing(self):

        if not self.processing_worker:
            return

        self.stop_button.setEnabled(
            False
        )

        self.progress_label.setText(
            "در حال توقف..."
        )

        self.logger.info(
            "درخواست توقف ارسال شد."
        )

        self.processing_worker.request_stop()

    # ========================================================
    # Log
    # ========================================================

    def append_log(
        self,
        message
    ):

        self.log_output.append(
            message
        )

        scrollbar = (
            self.log_output
            .verticalScrollBar()
        )

        scrollbar.setValue(
            scrollbar.maximum()
        )

    def clear_log(self):

        self.log_output.clear()

        self.logger.info(
            "Log توسط کاربر پاک شد."
        )

    def toggle_log(self):

        visible = (
            self.log_toggle_button.isChecked()
        )

        self.log_output.setVisible(
            visible
        )

        self.clear_log_button.setVisible(
            visible
        )

        if visible:

            self.log_toggle_button.setText(
                "بستن Log"
            )

        else:

            self.log_toggle_button.setText(
                "باز کردن Log"
            )

    # ========================================================
    # Style
    # ========================================================

    def _apply_style(self):

        self.setStyleSheet(
            """
            QMainWindow {
                background: #101114;
                color: #f2f2f2;
            }

            QWidget {
                color: #f2f2f2;
                font-size: 14px;
            }

            QScrollArea {
                background: #101114;
                border: none;
            }

            #title {
                font-size: 28px;
                font-weight: 700;
                padding: 8px;
            }

            #subtitle {
                color: #8f949c;
                font-size: 13px;
                padding-bottom: 8px;
            }

            #card {
                background: #181a1f;
                border: 1px solid #292c33;
                border-radius: 16px;
            }

            #sectionTitle {
                font-size: 18px;
                font-weight: 700;
                padding-bottom: 8px;
            }

            #fieldLabel {
                color: #c9cdd4;
                font-size: 13px;
                font-weight: 600;
                padding-top: 5px;
            }

            #pathLabel {
                background: #111318;
                border: 1px solid #292c33;
                border-radius: 10px;
                padding: 12px;
                color: #cfd3da;
            }

            #hint {
                color: #777d87;
                font-size: 12px;
                padding: 4px 0;
            }

            #status {
                color: #aeb4bd;
                font-size: 13px;
            }

            #footer {
                color: #5f646d;
                font-size: 11px;
                padding-top: 8px;
            }

            QLineEdit,
            QComboBox {
                background: #111318;
                border: 1px solid #30343c;
                border-radius: 10px;
                padding: 10px 12px;
                min-height: 20px;
            }

            QLineEdit:focus,
            QComboBox:focus {
                border: 1px solid #555b66;
            }

            QComboBox::drop-down {
                border: none;
                width: 30px;
            }

            QPushButton {
                background: #252830;
                border: 1px solid #353943;
                border-radius: 10px;
                padding: 10px 18px;
                min-height: 20px;
            }

            QPushButton:hover {
                background: #2d3038;
            }

            QPushButton:pressed {
                background: #202229;
            }

            QPushButton:disabled {
                color: #626771;
                background: #1a1c21;
            }

            #primaryButton {
                background: #f0f0f0;
                color: #111318;
                border: none;
                font-weight: 700;
            }

            #primaryButton:hover {
                background: #ffffff;
            }

            QListWidget {
                background: #111318;
                border: 1px solid #292c33;
                border-radius: 10px;
                padding: 6px;
            }

            QListWidget::item {
                padding: 9px;
                border-radius: 7px;
            }

            QListWidget::item:selected {
                background: #2a2e36;
            }

            QTextEdit {
                background: #0c0d10;
                border: 1px solid #292c33;
                border-radius: 10px;
                padding: 10px;
                color: #bfc5ce;
                font-family: Consolas;
                font-size: 12px;
            }

            QProgressBar {
                background: #111318;
                border: 1px solid #292c33;
                border-radius: 8px;
                text-align: center;
                min-height: 18px;
            }

            QProgressBar::chunk {
                background: #d9d9d9;
                border-radius: 7px;
            }

            QScrollBar:vertical {
                background: #111318;
                width: 12px;
                margin: 3px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background: #3a3e47;
                min-height: 40px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical:hover {
                background: #4a4f59;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
            """
        )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    import sys

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        APP_NAME
    )

    app.setFont(
        QFont(
            "Segoe UI",
            10
        )
    )

    window = MainWindow()

    window.show()

    sys.exit(
        app.exec()
    )