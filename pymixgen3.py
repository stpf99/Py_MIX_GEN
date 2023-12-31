import os
import random
import mutagen
from pydub import AudioSegment
from mutagen.mp3 import MP3
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QProgressBar, QLabel, QFileDialog, QSlider, QComboBox, QLineEdit, QFormLayout, QSpinBox
from PyQt5.QtCore import Qt, QTimer
import csv

class MixGenerator(QMainWindow):
    def __init__(self):
        super().__init__()

        self.lines = []
        self.input_directory = ""
        self.output_directory = ""
        self.output_name = "mixset.mp3"
        self.duration = 60 * 1000  # 60 minut w milisekundach
        self.crossfade_duration = 10  # 10 sekund
        self.base_key = "D"
        self.bpm_range = (20, 300)  # Przedział BPM
        self.min_track_length = 10  # Minimalna długość utworu w sekundach
        self.max_track_length = 600  # Maksymalna długość utworu w sekundach
        self.used_tracks = []
        self.initial_playlist = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_tracks)

        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)
        self.init_ui()

    def init_ui(self):
        self.progress_label = QLabel("Progress:")
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)

        self.duration_label = QLabel("Mixset Duration (minutes):")
        self.duration_slider = QSlider(Qt.Horizontal)
        self.duration_slider.setMinimum(1)
        self.duration_slider.setMaximum(180)
        self.duration_slider.setValue(60)
        self.duration_slider.valueChanged.connect(self.update_duration)

        self.duration_value_label = QLabel(f"Current Duration: {self.duration / 1000 / 60} minutes")

        self.crossfade_label = QLabel("Crossfade Duration (seconds):")
        self.crossfade_slider = QSlider(Qt.Horizontal)
        self.crossfade_slider.setMinimum(1)
        self.crossfade_slider.setMaximum(30)
        self.crossfade_slider.setValue(self.crossfade_duration)
        self.crossfade_slider.valueChanged.connect(self.update_crossfade_duration)

        self.crossfade_value_label = QLabel(f"Current Crossfade Duration: {self.crossfade_duration} seconds")

        self.base_key_label = QLabel("Base Key:")
        self.base_key_combo = QComboBox()
        self.base_key_combo.addItems(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])
        self.base_key_combo.currentIndexChanged.connect(self.update_base_key)

        self.min_bpm_label = QLabel("Minimum BPM:")
        self.min_bpm_spinbox = QSpinBox()
        self.min_bpm_spinbox.setMinimum(20)
        self.min_bpm_spinbox.setMaximum(300)
        self.min_bpm_spinbox.setValue(self.bpm_range[0])
        self.min_bpm_spinbox.valueChanged.connect(self.update_min_bpm)

        self.max_bpm_label = QLabel("Maximum BPM:")
        self.max_bpm_spinbox = QSpinBox()
        self.max_bpm_spinbox.setMinimum(20)
        self.max_bpm_spinbox.setMaximum(300)
        self.max_bpm_spinbox.setValue(self.bpm_range[1])
        self.max_bpm_spinbox.valueChanged.connect(self.update_max_bpm)

        self.min_track_length_spinbox = QSpinBox()
        self.min_track_length_spinbox.setMinimum(1)
        self.min_track_length_spinbox.setMaximum(600)
        self.min_track_length_spinbox.setValue(self.min_track_length)
        self.min_track_length_spinbox.valueChanged.connect(self.update_min_track_length)

        self.max_track_length_spinbox = QSpinBox()
        self.max_track_length_spinbox.setMinimum(1)
        self.max_track_length_spinbox.setMaximum(600)
        self.max_track_length_spinbox.setValue(self.max_track_length)
        self.max_track_length_spinbox.valueChanged.connect(self.update_max_track_length)

        self.input_directory_label = QLabel("Input Directory:")
        self.input_directory_line_edit = QLineEdit()
        self.input_directory_button = QPushButton("Browse")
        self.input_directory_button.clicked.connect(self.browse_input_directory)

        self.output_directory_label = QLabel("Output Directory:")
        self.output_directory_line_edit = QLineEdit()
        self.output_directory_button = QPushButton("Browse")
        self.output_directory_button.clicked.connect(self.browse_output_directory)

        self.output_name_label = QLabel("Output Name:")
        self.output_name_line_edit = QLineEdit()

        self.start_button = QPushButton("Generate Mixset")
        self.start_button.clicked.connect(self.generate_mixset)

        form_layout = QFormLayout()
        form_layout.addRow("Min Track Length (seconds):", self.min_track_length_spinbox)
        form_layout.addRow("Max Track Length (seconds):", self.max_track_length_spinbox)
        form_layout.addRow(self.min_bpm_label, self.min_bpm_spinbox)
        form_layout.addRow(self.max_bpm_label, self.max_bpm_spinbox)

        layout = QVBoxLayout()
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        layout.addWidget(self.input_directory_label)
        layout.addWidget(self.input_directory_line_edit)
        layout.addWidget(self.input_directory_button)

        layout.addWidget(self.duration_label)
        layout.addWidget(self.duration_slider)
        layout.addWidget(self.duration_value_label)

        layout.addWidget(self.crossfade_label)
        layout.addWidget(self.crossfade_slider)
        layout.addWidget(self.crossfade_value_label)

        layout.addWidget(self.base_key_label)
        layout.addWidget(self.base_key_combo)

        
        layout.addLayout(form_layout)

        layout.addWidget(self.output_directory_label)
        layout.addWidget(self.output_directory_line_edit)
        layout.addWidget(self.output_directory_button)

        layout.addWidget(self.output_name_label)
        layout.addWidget(self.output_name_line_edit)

        layout.addWidget(self.start_button)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def create_initial_playlist(self):
        index_file_path = os.path.join(self.input_directory, 'baza.txt')
        used_tracks_file_path = os.path.join(self.input_directory, 'used_tracks.txt')

        with open(index_file_path, 'r') as index_file:
            self.initial_playlist = []
            for line in index_file:
                line = line.strip().split(',')
                if len(line) == 4:
                    track_path, bpm, key, duration = line
                    # Dodaj utwór do wstępnej listy, jeśli nie jest oznaczony jako użyty
                    if not self.is_track_used(track_path):
                        self.initial_playlist.append({
                            'track_path': track_path,
                            'bpm': int(bpm),
                            'key': key,
                            'duration': int(duration)
                        })

            # Ustaw self.lines na skopiowaną listę utworów
            self.lines = self.initial_playlist.copy()

    def browse_input_directory(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        input_directory = QFileDialog.getExistingDirectory(self, "Select Input Directory", options=options)
        if input_directory:
            self.input_directory_line_edit.setText(input_directory)
            self.input_directory = os.path.normpath(input_directory)

            # Automatically start creating the database in the selected input directory
            self.create_database()

    def browse_output_directory(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        output_directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", options=options)
        if output_directory:
            self.output_directory_line_edit.setText(output_directory)
            self.output_directory = os.path.normpath(output_directory)

    def update_duration(self):
        self.duration = self.duration_slider.value() * 60 * 1000
        self.duration_value_label.setText(f"Current Duration: {self.duration / 1000 / 60} minutes")

    def update_crossfade_duration(self):
        self.crossfade_duration = self.crossfade_slider.value()
        self.crossfade_value_label.setText(f"Current Crossfade Duration: {self.crossfade_duration} seconds")

    def update_base_key(self, index):
        self.base_key = self.base_key_combo.itemText(index)

    def update_min_bpm(self):
        self.bpm_range = (self.min_bpm_spinbox.value(), self.bpm_range[1])

    def update_max_bpm(self):
        self.bpm_range = (self.bpm_range[0], self.max_bpm_spinbox.value())

    def update_min_track_length(self):
        self.min_track_length = self.min_track_length_spinbox.value()

    def update_max_track_length(self):
        self.max_track_length = self.max_track_length_spinbox.value()

    def generate_mixset(self):

        if self.timer.isActive():
            self.timer.stop()
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_tracks)
        self.timer.start(1000)
 
        self.used_tracks = []

        if not self.input_directory:
            print("Please select an input directory.")
            return

        if not self.output_directory:
            print("Please select an output directory.")
            return

        self.create_initial_playlist()  # Utwórz wstępną listę utworów

        self.output_name = self.output_name_line_edit.text()  # Use user input as the base name
        if not self.output_name:
            print("Please enter a valid output name.")
            return

        # Append KEY, BPM, and length to the output name
        self.output_name += f"-{self.base_key}-{self.bpm_range[0]}-{self.bpm_range[1]}-{self.duration / 1000 / 60}min.mp3"

        self.progress_bar.setValue(0)

        self.clear_old_playlist_entries()

        # Użyj wstępnej listy utworów do generowania mixsetu
        random.shuffle(self.initial_playlist)
        self.mixset = AudioSegment.silent(duration=0)

        self.total_tracks = len(self.initial_playlist)
        self.current_track = 0
        self.current_mix_length = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.process_tracks)
        self.timer.start(1000)  # Timer every second

        # Dodaj timer do monitorowania postępu
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)
        self.timer.start(1000)  # Timer every second

        # Add a slight delay before starting the progress timer to avoid conflicts
        QTimer.singleShot(500, self.start_progress_timer)

    def update_progress(self):
        # Ustaw postęp na pasku
        progress_value = int((self.current_mix_length / self.duration) * 100)
        self.progress_bar.setValue(progress_value)

    def clear_old_playlist_entries(self):
        # Remove older tracks from the playlist that were added in previous mixsets
        lines_to_remove = []
        for line in self.lines:
            _, _, _, _, title, _ = self.get_track_info_for_playlist(line)
            if title in self.used_tracks:
                lines_to_remove.append(line)

        for line in lines_to_remove:
            self.lines.remove(line)



    def save_used_track(self, track_info):
        used_tracks_file_path = os.path.join(self.input_directory, 'used_tracks.txt')
        with open(used_tracks_file_path, 'a') as used_tracks_file:
            used_tracks_file.write(f"{track_info}\n")

    def is_track_used(self, title):
        used_tracks_file_path = os.path.join(self.input_directory, 'used_tracks.txt')

        # Sprawdź, czy plik istnieje
        if not os.path.exists(used_tracks_file_path):
            # Jeśli plik nie istnieje, utwórz go
            with open(used_tracks_file_path, 'w'):
                pass  # Pusty blok - tworzenie pustego pliku

        with open(used_tracks_file_path, 'r') as used_tracks_file:
            used_tracks = used_tracks_file.read().splitlines()
            return title in used_tracks


    def process_tracks(self):
        print("Processing tracks...")

        # Zmniejsz granicę dla current_track i current_mix_length o 10 jednostek czasu
        time_margin = 10

        if self.current_track < self.total_tracks and self.current_mix_length < self.duration + time_margin:
            line = self.lines[self.current_track]
            bpm, key, track_length, artist, title, version = self.get_track_info_for_playlist(line)
            if title:
                print(f"Checking track: {title}")

                # Check if the track is already in used_tracks.txt
                if self.is_track_used(line['track_path']):
                    print(f"Skipping track {title} as it is already used.")
                    self.current_track += 1
                    self.update_progress()  # Update the progress bar
                    return

            if key is not None and (
                title not in [track['title'] for track in self.used_tracks] and
                key.startswith(self.base_key) and
                self.bpm_range[0] <= int(bpm) <= self.bpm_range[1] and
                self.min_track_length <= int(track_length) <= self.max_track_length

            ):
                print(f"Selecting track: {title}")
                audiofile = AudioSegment.from_file(line['track_path'])

                # Add fade-in only for the first track
                if not self.mixset:
                    fade_in_duration = min(self.crossfade_duration, len(audiofile) / 2)    
                    audiofile = audiofile.fade_in(fade_in_duration)
                    self.mixset = audiofile
                else:
                    # Add the track to the mixset with crossfade
                    self.mixset = self.mixset.append(audiofile, crossfade=self.crossfade_duration)

                # Add information about the added track to the list of used tracks
                self.used_tracks.append({
                    'title': title,
                    'artist': artist,
                    'version': version,
                    'time_added': self.current_mix_length,
                })

                # Save the used track to used_tracks.txt
                self.save_used_track(line['track_path'])

                self.current_mix_length += len(audiofile)

                print(f"Selected track: {title}")

            self.current_track += 1
            self.update_progress()  # Update the progress bar
        else:
            print("No title found for the current track.")
            # Stop both timers when the processing is complete
            self.timer.stop()
            self.progress_timer.stop()

            # Apply crossfade only if there is more than one track
            if len(self.used_tracks) > 1:
                fade_out_duration = min(self.crossfade_duration, len(self.mixset) / 2)    
                self.mixset = self.mixset.fade_out(fade_out_duration)

            output_path = os.path.join(self.output_directory, self.output_name)
            self.mixset.export(output_path, format='mp3')

            # Save used tracks to file
            with open(os.path.join(self.input_directory, 'used_tracks.txt'), 'a') as used_tracks_file:
                for track_info in self.used_tracks:
                    self.save_used_track(track_info)

            print("Mixset generated successfully.")
            print("Selected track list:")

            # Print the list of selected tracks
            for track_info in self.used_tracks:
                print(f" - {track_info['title']}")

            # Change: Generate and save the playlist
            self.generate_and_save_playlist()


    def start_progress_timer(self):
        self.progress_timer.start(100)  # Timer every 100 milliseconds


    def update_progress(self):
        progress_value = int((self.current_mix_length / self.duration) * 100)
        self.progress_bar.setValue(progress_value)

    def generate_and_save_playlist(self):
        playlist_lines = []

        def append_to_playlist(artist, title, version):
            playlist_line = f'{artist} - {title}'
            if version:
                playlist_line += f' ({version})'
            playlist_lines.append(playlist_line)

        # Sortuj utwory według czasu dodania do mixsetu
        sorted_used_tracks = sorted(self.used_tracks, key=lambda x: x['time_added'])

        for track in sorted_used_tracks:
            append_to_playlist(track['artist'], track['title'], track['version'])

        # Construct playlist file name based on user input, key, BPM, and mixset length
        playlist_file_name = f"{self.output_name_line_edit.text()}_playlist-{self.base_key}-{self.bpm_range[0]}-{self.bpm_range[1]}-{self.duration / 1000 / 60}min.txt"
        playlist_file_path = os.path.join(self.output_directory, playlist_file_name)

        # Save the playlist to the constructed file path
        with open(playlist_file_path, 'w') as playlist_file:
            playlist_file.write("\n".join(playlist_lines))

        print("Playlist generated and saved successfully.")


    def find_line_for_title(self, title):
        for line in self.lines:
            _, _, _, artist, current_title, _ = self.get_track_info_for_playlist(line)
            if current_title == title:
                return line
        return None


    def get_track_info_for_playlist(self, line):
        track_path = line['track_path']
        parts = track_path.strip().split(',')
        if len(parts) >= 1:
            try:
                audiofile = MP3(track_path)
                bpm = self.get_bpm(audiofile)
                key = self.get_key(audiofile)

                # Extract additional track information using mutagen
                version, remix = self.get_track_versions(audiofile)

                # Extract track length using mutagen
                track_length = self.get_track_length(track_path)

                # Extract artist and title from file path
                artist, title, _, _ = self.extract_artist_and_title(track_path)

                # Modify the version if it is empty
                if version == '':
                    version = 'original'

                return bpm, key, track_length, artist, title, version

            except Exception as e:
                print(f"Error getting track metadata for {track_path}: {e}")

        return None, None, None, None, None, None



    def get_bpm(self, audiofile):
        try:
            if 'TBPM' in audiofile:
                return int(audiofile['TBPM'].text[0])
        except Exception as e:
            print(f"Error extracting BPM: {e}")
        return 0

    def get_key(self, audiofile):
        try:
            if 'TKEY' in audiofile:
                return audiofile['TKEY'].text[0]
        except Exception as e:
            print(f"Error extracting key: {e}")
        return ''

    def get_track_versions(self, audiofile):
        version = ""
        remix = ""
        try:
            if 'TIT1' in audiofile:
                version = audiofile['TIT1'].text[0]
            if 'TIT2' in audiofile:
                title = audiofile['TIT2'].text[0]
                if "remix" in title.lower():
                    remix = title
        except Exception as e:
            print(f"Error extracting track versions: {e}")
        return version, remix

    def extract_artist_and_title(self, track_path):
        try:
            # Example: /path/to/artist - title (version) or (remix)artist -remix.mp3
            file_name = os.path.basename(track_path)
            parts = os.path.splitext(file_name)[0].split('-')    

            artist = ""
            title = ""
            version = ""
            remix = ""

            if len(parts) >= 2:
                artist = parts[0].strip()
                title = parts[1].strip()

                # If there are additional parts, consider them as version or remix
                if len(parts) > 2:
                    version = parts[2].strip()
                    remix = parts[-1].strip()

            return artist, title, version, remix

        except Exception as e:
            print(f"Error extracting artist and title: {e}")
            return "", "", "", ""

    def create_database(self):
        if not self.input_directory:
            print("Please select an input directory.")
            return

        database_file_path = os.path.normpath(os.path.join(self.input_directory, 'baza.txt'))

        # Check if 'baza.txt' exists, if not, create it
        if not os.path.exists(database_file_path):
            print("'baza.txt' not found in the selected input directory. Creating it...")
            self.create_database_file(database_file_path)

        print("Database creation complete.")

    def create_database_file(self, database_file_path):
        # Create 'baza.txt' containing information about each mp3 file
        with open(database_file_path, 'w', newline='') as database_file:
            csv_writer = csv.writer(database_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for root, dirs, files in os.walk(self.input_directory):
                for file in files:
                    if file.endswith('.mp3'):
                        file_path = os.path.join(root, file)
                        track_info = self.get_track_info(file_path)
                        if track_info:
                            bpm, key, track_length, _ = track_info
                            # Write information to 'baza.txt'
                            csv_writer.writerow([file_path, bpm, key, track_length])

        print("'baza.txt' created successfully.")

    def get_track_info(self, line):
        parts = line.strip().split(',')

        if len(parts) >= 1:
            track_path = parts[0]
            bpm, key, track_length = self.get_track_metadata(track_path)

            return bpm, key, track_length, track_path

        return None, None, None, None

    def get_track_metadata(self, track_path):
        try:
            audiofile = MP3(track_path)
            bpm = self.get_bpm(audiofile)
            key = self.get_key(audiofile)

            # Extract track length using mutagen
            track_length = self.get_track_length(track_path)

            return bpm, key, track_length

        except Exception as e:
            print(f"Error getting track metadata for {track_path}: {e}")
            return None, None, None


    def get_track_length(self, track_path):
        try:
            audiofile = MP3(track_path)
            # Use mutagen to get the track length in seconds
            return int(audiofile.info.length)
        except Exception as e:
            print(f"Error extracting track length for {track_path}: {e}")
            return None



if __name__ == "__main__":
    app = QApplication([])
    window = MixGenerator()
    window.show()
    app.exec_()