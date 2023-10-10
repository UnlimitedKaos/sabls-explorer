import sys
import math
from time import sleep
from explorer import SablsUnarchiver
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QStyleFactory, QGridLayout, QTreeWidget, 
    QTreeWidgetItem, QStyle, QSlider, QLabel, QMenuBar, QWidget, QMenu, 
    QVBoxLayout, QFileDialog, QProgressBar, QHBoxLayout, QPushButton, 
    QSizePolicy, QWidgetAction, QCheckBox, QTableWidget, QTableWidgetItem,
    QStackedWidget, QTabWidget, QHeaderView
)
from PySide6.QtGui import QAction, QGuiApplication, QColor, QShortcut
from PySide6.QtCore import Qt, Signal, QObject, QBuffer, QIODevice, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


class MainWindow(QMainWindow):
    class Signals(QObject):
        select_archive_signal = Signal()
        select_unarchive_signal = Signal()
        archive_index_progress = Signal(float)
        change_view_mode = Signal()
        select_file = Signal(int)
        load_file = Signal(bytes)
    
    def __init__(self):
        super().__init__()
        
        self.signals = MainWindow.Signals()
        
        self.archive_file = None
        self.archive_indices = None
        self.unarchive_dir = None
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        self.statusBar().addPermanentWidget(self.progress_bar)
        
        # Set window to a reasonable size
        self.resize(QGuiApplication.primaryScreen().availableGeometry().size() * 3/5)
        
        # Window title
        self.setWindowTitle("SABLS Explorer")
        
        # Create menu bar        
        self.setMenuBar(self.MenuBar(self))
        
        # Create content
        self.setCentralWidget(self.CentralWidget(self))
        
        # Create FileDialog
        self.dialogue = QFileDialog()
        
        
        # Set slots
        self.signals.select_archive_signal.connect(self.__open_archive_dialogue)
        self.signals.select_unarchive_signal.connect(self.__unarchive_dialogue)
        self.signals.archive_index_progress.connect(self.__indexing_status)
        self.signals.select_file.connect(self.__load_file)
        
        # Finish creating UI
        self.statusBar().showMessage("UI loaded", 1500)
    
    class MenuBar(QMenuBar):
        def __init__(self, parent: 'MainWindow') -> None:
            super().__init__(parent)
            
            self.main_window = parent
            
            file_menu = self.FileMenu(self)
            self.addMenu(file_menu)
            
            view_toggle = QAction("Toggle &View", self)
            view_toggle.triggered.connect(self.__view_toggle_handle)
            self.addAction(view_toggle)
        
        class FileMenu(QMenu):
            def __init__(self, parent: 'MainWindow.MenuBar'):
                super().__init__(parent)
                self.setTitle("&File")
                
                self.main_window = parent.main_window
                
                open_archive= QAction("Open Archive", self)
                open_archive.triggered.connect(self.__open_archive_handle)
                self.addAction(open_archive)
                
                self.addMenu(self.UnarchiveMenu(self))
            
            def __open_archive_handle(self, val):
                self.main_window.signals.select_archive_signal.emit()
            
            class UnarchiveMenu(QMenu):
                def __init__(self, parent: 'MainWindow.MenuBar.FileMenu'):
                    super().__init__(parent)
                    self.main_window = parent.main_window
                    
                    self.setTitle("Unarchive")
                    
                    dump_all = QAction("All", parent)
                    dump_all.triggered.connect(self.__dump_all_handle)
                    
                    dump_selected = QAction("Selected", parent)
                    dump_selected.triggered.connect(self.__dump_selected_handle)
                    self.addActions([dump_all, dump_selected])
                    
                def __dump_all_handle(self):
                    if self.main_window.archive_indices:
                        self.main_window.signals.select_unarchive_signal.emit()
                        if self.main_window.unarchive_dir:
                            SablsUnarchiver.dump_archive(self.main_window.unarchive_dir, self.main_window.archive_file, self.main_window.archive_indices)
                    else:
                        print("Nothing to save")
                
                def __dump_selected_handle(self):
                    if self.main_window.archive_indices:
                        def recurse(item: QTreeWidgetItem):
                            if not item.childCount():
                                check: MainWindow.CentralWidget.TreeView.CheckBox = self.main_window.centralWidget().tree_view.tree.itemWidget(item, 1)
                                if check.check_box.checkState() == Qt.CheckState.Checked:
                                    archive_label: MainWindow.CentralWidget.TreeView.ArchiveLabel = self.main_window.centralWidget().tree_view.tree.itemWidget(item, 0)
                                    self.main_window.statusBar().showMessage(f"Writing {archive_label.text}", 750)
                                    SablsUnarchiver.dump_file(
                                        self.main_window.unarchive_dir, 
                                        self.main_window.archive_file,
                                        self.main_window.archive_indices, 
                                        archive_label.index
                                    )
                            else:
                                for i in range(item.childCount()):
                                    recurse(item.child(i))
                        
                        self.main_window.signals.select_unarchive_signal.emit()
                        if self.main_window.unarchive_dir:
                            recurse(self.main_window.centralWidget().tree_view.tree.invisibleRootItem())
                    else:
                        print("Nothing to save")
        
        def __view_toggle_handle(self: QMenuBar):
            self.main_window.signals.change_view_mode.emit()
            print("Sorry, this isn't implemented yet")
    
    class CentralWidget(QWidget):
        class Signals(QObject):
            set_data = Signal()
        
        def __init__(self, parent: QMainWindow):
            super().__init__(parent)
            self.main_window = parent
            
            self.signals = self.Signals()
            
            root_layout = QHBoxLayout()
            
            self.tree_view = self.TreeView(self)
            self.music_content = self.MusicWidget(self)
            self.main_window.signals.load_file.connect(self.music_content.signals.load_file.emit)
            
            root_layout.addWidget(self.tree_view, 5)
            root_layout.addWidget(self.music_content, 2)
            self.setLayout(root_layout)
        
        class TreeView(QWidget):
            def __init__(self, parent:'MainWindow.CentralWidget'):
                super().__init__(parent)
                self.central_widget = parent
                self.main_window = parent.main_window
                
                layout = QGridLayout()
                
                self.tree = QTreeWidget()
                self.tree.setColumnCount(2)
                self.tree.setHeaderLabels(["Directory", "To Save"])
                self.tree.header().swapSections(1,0)
                self.tree.header().resizeSection(1, 60)
                
                
                self.central_widget.signals.set_data.connect(self.set_tree)
                self.tree.itemDoubleClicked.connect(self.selected)
                QShortcut(
                    Qt.Key.Key_Return, 
                    self.tree, 
                    context=Qt.ShortcutContext.WidgetShortcut,
                    activated=lambda: self.selected(self.tree.selectedItems()[0]) if self.tree.selectedItems() else None
                )
                
                layout.addWidget(self.tree)
                layout.setContentsMargins(0,0,0,0)
                self.setLayout(layout)
            
            def selected(self, item:QTreeWidgetItem):
                label = self.tree.itemWidget(item, 0)
                if isinstance(label, self.ArchiveLabel):
                    self.main_window.signals.select_file.emit(label.index)
            
            class CheckBox(QWidget):
                # A centered checkbox
                def __init__(self):
                    super().__init__()
                    layout = QHBoxLayout()
                    layout.setContentsMargins(0,0,0,0)
                    
                    self.check_box = QCheckBox()
                    
                    layout.addStretch()
                    layout.addWidget(self.check_box)
                    layout.addStretch()
                    self.setLayout(layout)
            
            class ArchiveLabel(QLabel):
                # Fundamentally a QLabel but contains the associated MainWindow.archive_indices' index
                def __init__(self, label:str, index:int):
                    super().__init__(label)
                    self.index = index
            
            def set_tree(self):
                # helper functions, idk if this practice is exactly kosher
                def tree_recursion(input:dict, parent:QTreeWidgetItem):  # Populate tree widget from paths
                    for key in input.keys():
                        level = QTreeWidgetItem(parent)
                        if isinstance(input[key], dict):  # populate level
                            level.setText(0, key)
                            tree_recursion(input[key], level)
                        else:  # end of path
                            self.tree.setItemWidget(level, 0, self.ArchiveLabel(key, input[key]))
                            self.tree.setItemWidget(level, 1, self.CheckBox())
                
                def path_recursion(input:list, layer:dict):  # Consolidate many path strings into a single object
                    if input[1:]:  # setup additional levels
                        if input[0] not in layer.keys():
                            layer.update({input[0]: {}})
                        path_recursion(input[1:], layer[input[0]])
                    else:  # end of path
                        layer.update({input[0]: i})
                
                self.tree.clear()
                paths = {}
                unnamed = "No Name"  # prefix for unnamed records
                for i, indexed in enumerate(self.central_widget.main_window.archive_indices):
                    path: str = indexed[1].strip(b'\0').decode('ascii')
                    if path == "":
                        path = unnamed + "\\" + F"File {i:04d}"
                    path_recursion(path.split("\\"), paths)
                
                tree_recursion(paths, self.tree.invisibleRootItem())
        
        class MusicWidget(QWidget):
            class Signals(QObject):
                load_file = Signal(bytes)
                unload = Signal()
            
            def __init__(self, parent: 'MainWindow.CentralWidget'):
                super().__init__(parent)
                
                self.signals = self.Signals()
                
                self.media_player = QMediaPlayer()
                self.audio_output = QAudioOutput()
                self.media_player.setAudioOutput(self.audio_output)
                self.buffer = QBuffer()
                
                layout = QVBoxLayout()
                
                self.setMaximumWidth(350)
                
                self.art = self.Art(self)
                self.controls = self.Controls(self)
                self.info = self.Info(self)
                
                layout.addWidget(self.art, 3)
                layout.addWidget(self.controls)
                layout.addWidget(self.info, 2)
                layout.setContentsMargins(0,0,0,0)
                self.setLayout(layout)
                
                self.signals.load_file.connect(self.load_media)
                self.signals.unload.connect(self.unload)
                self.media_player.errorChanged.connect(lambda error: print("Media Player Error: {}".format(error)))            
            
            class Art(QWidget):
                def __init__(self, parent: 'MainWindow.CentralWidget.MusicWidget'):
                    super().__init__()
                    layout = QGridLayout()
                    
                    root_widget = QLabel("Music Visuals")
                    root_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    root_widget.setStyleSheet("background: orange")
                    
                    layout.addWidget(root_widget)
                    layout.setContentsMargins(0,0,0,0)
                    self.setLayout(layout)
            
            class Controls(QWidget):
                class Signals(QObject):
                    set_enabled = Signal(bool)
                
                def __init__(self, parent: 'MainWindow.CentralWidget.MusicWidget'):
                    super().__init__(parent)
                    self.music_widget = parent
                    self.signals = self.Signals()
                    
                    layout = QGridLayout()
                    self.setFixedHeight(100)
                    
                    time_slider = self.TimeBar(self)
                    play_pause = self.PlayPause(self)
                    stop = self.Stop(self)                
                    volume = self.Volume(self)
                    
                    layout.addWidget(time_slider, 0,0, 1,4)
                    layout.addWidget(play_pause, 1,0)
                    layout.addWidget(stop, 1,1)
                    layout.addWidget(volume, 1,3)
                    
                    layout.setRowStretch(0, 1)
                    layout.setRowStretch(1, 3)
                    
                    layout.setColumnStretch(0, 1)
                    layout.setColumnStretch(1, 1)
                    layout.setColumnStretch(2, 2)
                    layout.setColumnStretch(3, 1)
                    
                    layout.setContentsMargins(0,0,0,0)
                    
                    self.setLayout(layout)
                    
                    self.signals.set_enabled.connect(time_slider.signals.set_enabled.emit)
                    self.signals.set_enabled.connect(play_pause.signals.set_enabled.emit)
                    self.signals.set_enabled.connect(stop.setEnabled)
                    
                    self.signals.set_enabled.emit(False)
                
                class PlayPause(QPushButton):
                    class Signals(QObject):
                        set_enabled = Signal(bool)
                    
                    def __init__(self, parent: 'MainWindow.CentralWidget.MusicWidget.Controls'):
                        super().__init__()
                        self.media_player = parent.music_widget.media_player
                        self.signals = self.Signals()
                        
                        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                        
                        
                        self.clicked.connect(self.__toggle_mode)
                        self.media_player.playbackStateChanged.connect(self.__match_icon_to_mode)
                        self.signals.set_enabled.connect(self.__enabled)
                    
                    def __toggle_mode(self, a):
                        match self.media_player.playbackState():
                            case QMediaPlayer.PlaybackState.StoppedState | QMediaPlayer.PlaybackState.PausedState:
                                self.media_player.play()
                            
                            case QMediaPlayer.PlaybackState.PlayingState:
                                self.media_player.pause()
                            
                            case _:
                                self.media_player.stop()
                                print("Playback State not handled: ", print(self.media_player.playbackState()))
                    
                    def __match_icon_to_mode(self, mode: QMediaPlayer.PlaybackState):
                        match mode:
                            case QMediaPlayer.PlaybackState.StoppedState | QMediaPlayer.PlaybackState.PausedState:
                                self.__paused()
                            
                            case QMediaPlayer.PlaybackState.PlayingState:
                                self.__playing()
                    
                    def __playing(self):
                        self.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))  # button is to pause music
                    
                    def __paused(self):
                        self.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))  # button is to play music
                    
                    def __enabled(self, enabled:bool):
                        if enabled:
                            self.setEnabled(True)
                        else:
                            self.__paused()
                            self.setEnabled(False)
                
                class Stop(QPushButton):
                    class Signals(QObject):
                        reset_pause_button = Signal()
                    
                    def __init__(self, parent: 'MainWindow.CentralWidget.MusicWidget.Controls'):
                        super().__init__()
                        self.signals = self.Signals()
                        self.media_player = parent.music_widget.media_player
                        self.pause_button = parent
                        
                        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                        
                        self.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
                        
                        self.clicked.connect(self.__stop)
                    
                    def __stop(self):
                        self.media_player.stop()
                        self.signals.reset_pause_button.emit()
                
                class Volume(QPushButton):
                    def __init__(self, parent: 'MainWindow.CentralWidget.MusicWidget.Controls'):
                        super().__init__()
                        self.media_player = parent.music_widget.media_player
                        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                        
                        self.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
                        
                        menu = QMenu(self)
                        menu.setFixedWidth(70)
                        
                        volume_root = QWidget()
                        volume_root_layout = QGridLayout()
                        volume_action = QWidgetAction(self)
                        self.volume_slider = QSlider()
                        self.volume_slider.setRange(0, 100)
                        self.__match_volume()
                        volume_root_layout.addWidget(self.volume_slider)
                        volume_root_layout.setContentsMargins(0,-1,0,-1)
                        volume_root.setLayout(volume_root_layout)
                        volume_action.setDefaultWidget(volume_root)
                        
                        mute_action = QWidgetAction(self)
                        self.mute_button = QPushButton()
                        self.mute_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted))
                        self.__match_mute()
                        mute_action.setDefaultWidget(self.mute_button)
                        
                        menu.addAction(volume_action)
                        menu.addAction(mute_action)
                        self.setMenu(menu)
                        
                        self.media_player.audioOutput().mutedChanged.connect(self.__match_mute)
                        self.media_player.audioOutput().volumeChanged.connect(self.__match_volume)
                        self.mute_button.clicked.connect(self.__toggle_mute)
                        self.volume_slider.valueChanged.connect(self.__set_volume)
                    
                    def __match_mute(self):
                        if self.media_player.audioOutput().isMuted():
                            self.__muted()
                        else:
                            self.__unmuted()
                    
                    def __muted(self):
                        self.mute_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
                        self.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted))
                    
                    def __unmuted(self):
                        self.mute_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted))
                        self.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
                    
                    def __toggle_mute(self):
                        self.media_player.audioOutput().setMuted(not self.media_player.audioOutput().isMuted())
                    
                    def __match_volume(self):
                        self.volume_slider.setValue(int(self.media_player.audioOutput().volume() * 100))
                    
                    def __set_volume(self, val):
                        self.media_player.audioOutput().setVolume(val/100)
                
                class TimeBar(QWidget):
                    class Signals(QObject):
                        set_enabled = Signal(bool)
                    
                    def __init__(self, parent: 'MainWindow.CentralWidget.MusicWidget.Controls'):
                        super().__init__()
                        self.media_player = parent.music_widget.media_player
                        self.signals = self.Signals()
                        
                        self.setFixedHeight(33)
                        layout = QHBoxLayout()
                        
                        self.slider = QSlider()
                        self.slider.setPageStep(0)  # disables clicking the groove
                        self.slider.setRange(0,100)
                        self.slider.setOrientation(Qt.Orientation.Horizontal)
                        
                        self.elapsed = QLabel("--:--")
                        self.elapsed.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        
                        self.duration = QLabel("--:--")
                        self.duration.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        
                        layout.addWidget(self.elapsed, 1)
                        layout.addWidget(self.slider,  3)
                        layout.addWidget(self.duration,  1)
                        layout.setContentsMargins(0,0,0,0)
                        self.setLayout(layout)
                        
                        self.signals.set_enabled.connect(self.__set_enabled)
                        
                        self.media_player.positionChanged.connect(self.__match_position)
                        self.slider.sliderMoved.connect(lambda: self.media_player.setPosition(int(self.slider.value()/100 * self.media_player.duration())))
                    
                    def __set_enabled(self, enabled:bool):
                        if not enabled:
                            self.elapsed.setText("--:--")
                            self.duration.setText("--:--")
                            self.slider.setStyleSheet("QSlider::handle:horizontal {background:#00000000}")
                        else:
                            self.slider.setStyleSheet("QSlider::handle:horizontal {}")
                            self.__match_position()
                        self.setEnabled(enabled)
                    
                    def __match_position(self):
                        def position_to_string(position):
                            hours = "{}:".format(math.floor((position / 1000) / (60 * 60))) if math.floor((position / 1000) / (60 * 60)) > 0 else ""
                            minutes = "{:02d}:".format(math.floor((position / 1000) / 60)) # if math.floor((position / 1000) / 60) > 0 else "--:"
                            seconds = "{:02d}".format(math.floor((position / 1000) % 60))
                            millis = "{:0.3f}".format((position / 1000) % 1)
                            
                            return hours + minutes + seconds + millis[1:4]
                        self.elapsed.setText(position_to_string(self.media_player.position()))
                        self.duration.setText(position_to_string(self.media_player.duration()))
                        if not self.slider.isSliderDown():
                            self.slider.setValue((self.media_player.position() / self.media_player.duration()) * 100)
            
            class Info(QWidget):
                def __init__(self, parent: 'MainWindow.CentralWidget.MusicWidget'):
                    super().__init__()
                    
                    self.media_player = parent.media_player
                    
                    layout = QGridLayout()
                    
                    self.display_stack = QStackedWidget()
                    
                    
                    default_widget = QLabel("")
                    default_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    infos = QTabWidget()
                    
                    self.metadata_table = QTableWidget()
                    self.metadata_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    self.metadata_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                    self.metadata_table.verticalHeader().hide()
                    
                    self.file_info = QTableWidget()
                    self.file_info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    self.file_info.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                    self.file_info.verticalHeader().hide()
                    
                    infos.addTab(self.metadata_table, "Metadata")
                    infos.addTab(self.file_info, "File Info")
                    
                    self.display_stack.addWidget(default_widget)
                    # Im too lazy to implement the file info so tabs aren't needed yet
                    #self.display_stack.addWidget(infos)
                    self.display_stack.addWidget(self.metadata_table)
                    
                    layout.addWidget(self.display_stack)
                    layout.setContentsMargins(0,0,0,0)
                    self.setLayout(layout)
                    
                    self.media_player.metaDataChanged.connect(self.__set_metadata)
                
                def __set_metadata(self):
                    if len(self.media_player.metaData().keys()) > 0:  # metadata to display
                        self.display_stack.setCurrentIndex(1)
                        self.metadata_table.setColumnCount(2)
                        self.metadata_table.setRowCount(len(self.media_player.metaData().keys()))
                        self.metadata_table.setHorizontalHeaderLabels(["Tag", "Value"])
                        for i, key in enumerate(self.media_player.metaData().keys()):
                            tag = QTableWidgetItem(key.name)
                            val = QTableWidgetItem(self.media_player.metaData().stringValue(key))
                            self.metadata_table.setItem(i, 0, tag)
                            self.metadata_table.setItem(i, 1, val)
                    else:  # file unloaded
                        self.display_stack.setCurrentIndex(0)
                        self.metadata_table.clear()
                        #self.file_info.clear()
                
                def __make_example_table(self, table: QTableWidget):
                    colors = [
                        ("Red", "#FF0000"),
                        ("Green", "#00FF00"),
                        ("Blue", "#0000FF"),
                        ("Black", "#000000"),
                        ("White", "#FFFFFF"),
                        ("Electric Green", "#41CD52"),
                        ("Dark Blue", "#222840"),
                        ("Yellow", "#F9E56d")
                    ]
                    
                    def get_rgb_from_hex(code):
                        code_hex = code.replace("#", "")
                        rgb = tuple(int(code_hex[i:i+2], 16) for i in (0, 2, 4))
                        return QColor.fromRgb(rgb[0], rgb[1], rgb[2])
                    
                    table.setRowCount(len(colors))
                    table.setColumnCount(len(colors[0]) + 1)
                    table.setHorizontalHeaderLabels(["Name", "Hex Code", "Color"])
                    
                    for i, (name, code) in enumerate(colors):
                        item_name = QTableWidgetItem(name)
                        item_code = QTableWidgetItem(code)
                        item_color = QTableWidgetItem()
                        item_color.setBackground(get_rgb_from_hex(code))
                        table.setItem(i, 0, item_name)
                        table.setItem(i, 1, item_code)
                        table.setItem(i, 2, item_color)
            
            def load_media(self, data:bytes):
                if self.buffer.isOpen():
                    self.unload()
                self.buffer.setData(data)
                self.buffer.open(QIODevice.OpenModeFlag.ReadOnly)
                self.buffer.reset()  # same as seek(0)?
                self.media_player.setSourceDevice(self.buffer, QUrl.fromLocalFile("./"))
                print("Audio loaded")
                self.controls.signals.set_enabled.emit(True)
            
            def unload(self):
                if self.media_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
                    self.media_player.stop()
                sleep(0.125)  # Avoids what seem to be a race condition with following line
                self.media_player.setSourceDevice(None)
                self.buffer.close()
                self.controls.signals.set_enabled.emit(False)
    
    indexing_status_init = False
    def __indexing_status(self, progress: float):
        if progress == float('inf'):
            self.indexing_status_init = False
            self.progress_bar.hide()
            self.statusBar().showMessage("Finished", 1500)
        else:
            if not self.indexing_status_init:
                self.indexing_status_init = True
                self.progress_bar.setFixedSize(self.geometry().width()-120, self.statusBar().size().height()-5)
                self.progress_bar.show()
                self.statusBar().showMessage("Indexing: ", 0)
            
            self.progress_bar.setValue(int(progress))
    
    def __unarchive_dialogue(self):
        path = self.dialogue.getExistingDirectory(self, "Unarchive Path")
        if path == '':
            self.unarchive_dir = None
        else:
            self.unarchive_dir = Path(path) / self.archive_name
        
    
    def __open_archive_dialogue(self):
        (file, open_filter) = self.dialogue.getOpenFileName(self.dialogue, "Open Archive", "./", "COD Black Ops Audio Archive(*.sabl *.sabs)")
        if file == '':
            return
        file = Path(file)
        self.statusBar().showMessage("Loading archive...", 0)
        sleep(0.05)
        self.__load_archive(file)
    
    def __load_archive(self, file: Path):
        self.archive_name = file.name
        self.archive_file = SablsUnarchiver.load_archive(file)
        self.archive_indices = SablsUnarchiver.find_flacs(
            self.archive_file,
            progress_callback = lambda x: self.signals.archive_index_progress.emit(x)
        )
        
        if not self.archive_indices:
            print("Empty Archive")
        else:
            self.centralWidget().signals.set_data.emit()
    
    def __load_file(self, archive_index):
        self.signals.load_file.emit(
            SablsUnarchiver.select_file(self.archive_file, self.archive_indices, archive_index)
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
