using Microsoft.Win32;
using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using Forms = System.Windows.Forms;
using Drawing = System.Drawing;

namespace BuryaPresetEditor
{
    public partial class MainWindow : Window, INotifyPropertyChanged
    {
        private JsonObject? _rootJson;
        private string? _currentFilePath;
        private string? _resourceFolderPath;
        private WeatherHour? _selectedHour;
        private WeatherHour? _copiedHour;
        private WeatherHour? _copiedParameterSource;
        private CopyParameterMode _copiedParameterMode;
        private PresetFile? _selectedPresetFile;
        private string _resourceFolderText = "Не выбрана";
        private string _selectedGrassPresetName = "default";
        private string _selectedEditorMode = "Lighting";
        private string _presetListHeader = "Lighting JSON:";
        private string _tableHeader = "Часы";
        private string _rightPanelHeader = "Редактор выбранного часа";
        private double _worldMapSunAzimuth;
        private double _worldMapSunHeight;
        private string _weatherLocationId = "";
        private string _weatherPresetName = "";
        private string _weatherSourcePresetName = "";
        private string _weatherType = "rain";
        private bool _isFileMonitoringEnabled;
        private string _selectedAutoReloadMode = "Спрашивать при конфликте";
        private string _monitorStatusText = "Мониторинг выключен";
        private bool _hasUnsavedChanges;
        private bool _isLoadingFile;
        private bool _isSavingFromEditor;
        private DateTime _ignoreWatcherUntil = DateTime.MinValue;
        private FileSystemWatcher? _fileWatcher;
        private DispatcherTimer? _reloadDebounceTimer;
        private bool _isTableExpanded;
        private GridLength _savedLeftColumnWidth;
        private GridLength _savedLeftSplitterColumnWidth;
        private GridLength _savedCenterColumnWidth;
        private GridLength _savedRightSplitterColumnWidth;
        private GridLength _savedRightColumnWidth;
        private double _savedLeftColumnMinWidth;
        private double _savedLeftSplitterColumnMinWidth;
        private double _savedCenterColumnMinWidth;
        private double _savedRightSplitterColumnMinWidth;
        private double _savedRightColumnMinWidth;

        public ObservableCollection<WeatherHour> Hours { get; set; }
        public ObservableCollection<string> OpenedFiles { get; set; }
        public ObservableCollection<string> EditorModes { get; set; }
        public ObservableCollection<string> AutoReloadModes { get; set; }
        public ObservableCollection<PresetFile> LightingPresetFiles { get; set; }
        public ObservableCollection<PresetFile> WorldMapPresetFiles { get; set; }
        public ObservableCollection<PresetFile> WeatherPresetFiles { get; set; }
        public ObservableCollection<PresetFile> VisiblePresetFiles { get; set; }
        public ObservableCollection<string> GrassPresetNames { get; set; }

        public WeatherHour? SelectedHour
        {
            get => _selectedHour;
            set
            {
                _selectedHour = value;
                OnPropertyChanged(nameof(SelectedHour));
            }
        }

        public PresetFile? SelectedPresetFile
        {
            get => _selectedPresetFile;
            set
            {
                _selectedPresetFile = value;
                OnPropertyChanged(nameof(SelectedPresetFile));
            }
        }

        public string ResourceFolderText
        {
            get => _resourceFolderText;
            set
            {
                _resourceFolderText = value;
                OnPropertyChanged(nameof(ResourceFolderText));
            }
        }

        public string SelectedGrassPresetName
        {
            get => _selectedGrassPresetName;
            set
            {
                _selectedGrassPresetName = NormalizeGrassName(value);
                OnPropertyChanged(nameof(SelectedGrassPresetName));
                MarkDirty();
            }
        }

        public string SelectedEditorMode
        {
            get => _selectedEditorMode;
            set
            {
                _selectedEditorMode = value;
                OnPropertyChanged(nameof(SelectedEditorMode));
                RefreshVisiblePresetFiles();
                UpdateModeLabels();
                ApplyModeVisibility();
            }
        }

        public string PresetListHeader
        {
            get => _presetListHeader;
            set
            {
                _presetListHeader = value;
                OnPropertyChanged(nameof(PresetListHeader));
            }
        }

        public string TableHeader
        {
            get => _tableHeader;
            set
            {
                _tableHeader = value;
                OnPropertyChanged(nameof(TableHeader));
            }
        }

        public string RightPanelHeader
        {
            get => _rightPanelHeader;
            set
            {
                _rightPanelHeader = value;
                OnPropertyChanged(nameof(RightPanelHeader));
            }
        }

        public double WorldMapSunAzimuth
        {
            get => _worldMapSunAzimuth;
            set
            {
                _worldMapSunAzimuth = WeatherHour.RoundNumber(value);
                OnPropertyChanged(nameof(WorldMapSunAzimuth));
                MarkDirty();
            }
        }

        public double WorldMapSunHeight
        {
            get => _worldMapSunHeight;
            set
            {
                _worldMapSunHeight = WeatherHour.RoundNumber(value);
                OnPropertyChanged(nameof(WorldMapSunHeight));
                MarkDirty();
            }
        }

        public string WeatherLocationId
        {
            get => _weatherLocationId;
            set
            {
                _weatherLocationId = value;
                OnPropertyChanged(nameof(WeatherLocationId));
                MarkDirty();
            }
        }

        public string WeatherPresetName
        {
            get => _weatherPresetName;
            set
            {
                _weatherPresetName = value;
                OnPropertyChanged(nameof(WeatherPresetName));
                MarkDirty();
            }
        }

        public string WeatherSourcePresetName
        {
            get => _weatherSourcePresetName;
            set
            {
                _weatherSourcePresetName = value;
                OnPropertyChanged(nameof(WeatherSourcePresetName));
                MarkDirty();
            }
        }

        public string WeatherType
        {
            get => _weatherType;
            set
            {
                _weatherType = value;
                OnPropertyChanged(nameof(WeatherType));
                MarkDirty();
            }
        }

        public bool IsFileMonitoringEnabled
        {
            get => _isFileMonitoringEnabled;
            set
            {
                _isFileMonitoringEnabled = value;
                OnPropertyChanged(nameof(IsFileMonitoringEnabled));
                RestartFileWatcher();
            }
        }

        public string SelectedAutoReloadMode
        {
            get => _selectedAutoReloadMode;
            set
            {
                _selectedAutoReloadMode = value;
                OnPropertyChanged(nameof(SelectedAutoReloadMode));
            }
        }

        public string MonitorStatusText
        {
            get => _monitorStatusText;
            set
            {
                _monitorStatusText = value;
                OnPropertyChanged(nameof(MonitorStatusText));
            }
        }

        public event PropertyChangedEventHandler? PropertyChanged;

        public MainWindow()
        {
            InitializeComponent();

            Hours = new ObservableCollection<WeatherHour>();
            OpenedFiles = new ObservableCollection<string>();
            EditorModes = new ObservableCollection<string>();
            AutoReloadModes = new ObservableCollection<string>();
            LightingPresetFiles = new ObservableCollection<PresetFile>();
            WorldMapPresetFiles = new ObservableCollection<PresetFile>();
            WeatherPresetFiles = new ObservableCollection<PresetFile>();
            VisiblePresetFiles = new ObservableCollection<PresetFile>();
            GrassPresetNames = new ObservableCollection<string>();

            EditorModes.Add("Lighting");
            EditorModes.Add("World Map");
            EditorModes.Add("Weather");

            AutoReloadModes.Add("Автообновлять всегда");
            AutoReloadModes.Add("Спрашивать при конфликте");
            AutoReloadModes.Add("Не обновлять, если есть несохранённые изменения");

            OpenedFiles.Add("Файл не открыт");
            GrassPresetNames.Add("default");

            CreateDefaultRows(24);

            DataContext = this;
            UpdateModeLabels();
            ApplyModeVisibility();

            _reloadDebounceTimer = new DispatcherTimer
            {
                Interval = TimeSpan.FromMilliseconds(500)
            };
            _reloadDebounceTimer.Tick += ReloadDebounceTimer_Tick;
        }

        private EditorMode CurrentMode
        {
            get
            {
                return SelectedEditorMode switch
                {
                    "World Map" => EditorMode.WorldMap,
                    "Weather" => EditorMode.Weather,
                    _ => EditorMode.Lighting
                };
            }
        }

        private void CreateDefaultRows(int count)
        {
            Hours.Clear();

            for (int i = 0; i < count; i++)
            {
                Hours.Add(new WeatherHour
                {
                    Hour = i,
                    SunColorText = "1,1,1",
                    SunIntensity = 1.0,
                    AmbientColorText = "1,1,1",
                    AmbientIntensity = 1.0,
                    FogColorText = "0,0,0",
                    FogDensity = 0.002,
                    Exposure = 1.0,
                    ShadowAO = 0.6,
                    Emission = 0.0,
                    BloomIntensity = 1.0,
                    BloomSoftThreshold = 0.5,
                    BloomThreshold = 3.0,
                    HdrTexture = "",
                    SeaColorText = "0,0,0",
                    SeaParamsText = "0,0,0",
                    SeaSkyColorText = "0,0,0"
                });
            }

            SubscribeToRows();
            SelectedHour = Hours.FirstOrDefault();
        }

        private void SubscribeToRows()
        {
            foreach (WeatherHour row in Hours)
            {
                row.PropertyChanged -= Row_PropertyChanged;
                row.PropertyChanged += Row_PropertyChanged;
            }
        }

        private void Row_PropertyChanged(object? sender, PropertyChangedEventArgs e)
        {
            MarkDirty();
        }

        private void MarkDirty()
        {
            if (_isLoadingFile || _isSavingFromEditor)
                return;

            _hasUnsavedChanges = true;
            UpdateMonitorStatus();
        }

        private void ClearDirty()
        {
            _hasUnsavedChanges = false;
            UpdateMonitorStatus();
        }

        private void UpdateMonitorStatus(string? customText = null)
        {
            if (!string.IsNullOrWhiteSpace(customText))
            {
                MonitorStatusText = customText;
                return;
            }

            string monitorState = IsFileMonitoringEnabled ? "Мониторинг включён" : "Мониторинг выключен";
            string dirtyState = _hasUnsavedChanges ? "есть несохранённые изменения" : "нет несохранённых изменений";
            MonitorStatusText = $"{monitorState}, {dirtyState}";
        }

        private void ApplyModeVisibility()
        {
            if (!IsInitialized || HoursGrid == null)
                return;

            bool isLighting = CurrentMode == EditorMode.Lighting;
            bool isWorldMap = CurrentMode == EditorMode.WorldMap;
            bool isWeather = CurrentMode == EditorMode.Weather;

            SetColumnVisibility(1, true);                         // Sun Color
            SetColumnVisibility(2, true);                         // Sun Intensity
            SetColumnVisibility(3, true);                         // Ambient Color
            SetColumnVisibility(4, true);                         // Ambient Intensity
            SetColumnVisibility(5, isLighting || isWorldMap);      // Fog Color
            SetColumnVisibility(6, true);                         // Fog Density
            SetColumnVisibility(7, isLighting || isWorldMap);      // Exposure
            SetColumnVisibility(8, true);                         // Shadow AO
            SetColumnVisibility(9, isLighting || isWorldMap);      // Emission
            SetColumnVisibility(10, isLighting || isWorldMap);     // Bloom Intensity
            SetColumnVisibility(11, isLighting || isWorldMap);     // Bloom Soft
            SetColumnVisibility(12, isLighting || isWorldMap);     // Bloom Threshold
            SetColumnVisibility(13, isLighting || isWorldMap);     // HDR
            SetColumnVisibility(14, isLighting || isWorldMap);     // Sea / Deep Color
            SetColumnVisibility(15, isLighting);                  // Sea Params
            SetColumnVisibility(16, isLighting || isWorldMap);     // Sea Sky / Shallow

            SetElementVisibility("GrassPresetPanel", isLighting);
            SetElementVisibility("WorldMapRootPanel", isWorldMap);
            SetElementVisibility("WeatherRootPanel", isWeather);

            SetElementVisibility("FogColorPanel", isLighting || isWorldMap);
            SetElementVisibility("ExposurePanel", isLighting || isWorldMap);
            SetElementVisibility("EmissionPanel", isLighting || isWorldMap);
            SetElementVisibility("BloomPanel", isLighting || isWorldMap);
            SetElementVisibility("HdrPanel", isLighting || isWorldMap);
            SetElementVisibility("SeaColorPanel", isLighting || isWorldMap);
            SetElementVisibility("SeaParamsPanel", isLighting);
            SetElementVisibility("SeaSkyPanel", isLighting || isWorldMap);

            if (isWorldMap)
            {
                SetColumnHeader(0, "Season");
                SetColumnHeader(14, "Deep Color");
                SetColumnHeader(16, "Shallow Color");
                SetTextBlockText("SeaColorLabel", "Deep Color:");
                SetTextBlockText("SeaSkyLabel", "Shallow Color:");
            }
            else
            {
                SetColumnHeader(0, "Hour");
                SetColumnHeader(14, "Sea Color");
                SetColumnHeader(16, "Sea Sky Color");
                SetTextBlockText("SeaColorLabel", "Sea Color:");
                SetTextBlockText("SeaSkyLabel", "Sea Sky Color:");
            }
        }

        private void SetColumnVisibility(int columnIndex, bool visible)
        {
            if (columnIndex < 0 || columnIndex >= HoursGrid.Columns.Count)
                return;

            HoursGrid.Columns[columnIndex].Visibility = visible ? Visibility.Visible : Visibility.Collapsed;
        }

        private void SetColumnHeader(int columnIndex, string header)
        {
            if (columnIndex < 0 || columnIndex >= HoursGrid.Columns.Count)
                return;

            HoursGrid.Columns[columnIndex].Header = header;
        }

        private void SetElementVisibility(string elementName, bool visible)
        {
            if (FindName(elementName) is FrameworkElement element)
                element.Visibility = visible ? Visibility.Visible : Visibility.Collapsed;
        }

        private void SetTextBlockText(string elementName, string text)
        {
            if (FindName(elementName) is TextBlock textBlock)
                textBlock.Text = text;
        }

        private void SelectResourceFolder_Click(object sender, RoutedEventArgs e)
        {
            using Forms.FolderBrowserDialog dialog = new Forms.FolderBrowserDialog
            {
                Description = "Выбери папку resource игры",
                UseDescriptionForTitle = true,
                ShowNewFolderButton = false
            };

            if (dialog.ShowDialog() != Forms.DialogResult.OK)
                return;

            try
            {
                LoadResourceFolder(dialog.SelectedPath);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка чтения resource папки:\n{ex.Message}", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void LoadResourceFolder(string resourceFolderPath)
        {
            if (!Directory.Exists(resourceFolderPath))
                throw new Exception("Папка не существует.");

            _resourceFolderPath = resourceFolderPath;
            ResourceFolderText = resourceFolderPath;

            LoadTextureLibrary(resourceFolderPath);
            ScanAllPresets(resourceFolderPath);
            RefreshVisiblePresetFiles();
        }

        private void LoadTextureLibrary(string resourceFolderPath)
        {
            GrassPresetNames.Clear();

            string textureLibraryPath = Path.Combine(resourceFolderPath, "texture_library.json");

            if (!File.Exists(textureLibraryPath))
            {
                GrassPresetNames.Add("default");
                SelectedGrassPresetName = "default";
                return;
            }

            string jsonText = File.ReadAllText(textureLibraryPath);
            JsonNode? parsedNode = JsonNode.Parse(jsonText);

            if (parsedNode is not JsonObject rootObject || rootObject["grass_preset"] is not JsonObject grassObject)
            {
                GrassPresetNames.Add("default");
                SelectedGrassPresetName = "default";
                return;
            }

            foreach (string key in grassObject.Select(pair => pair.Key).OrderBy(name => name))
            {
                string cleanName = NormalizeGrassName(key);

                if (!GrassPresetNames.Contains(cleanName))
                    GrassPresetNames.Add(cleanName);
            }

            if (GrassPresetNames.Count == 0)
                GrassPresetNames.Add("default");

            if (!GrassPresetNames.Contains(SelectedGrassPresetName))
                SelectedGrassPresetName = GrassPresetNames.Contains("default") ? "default" : GrassPresetNames[0];
        }

        private void ScanAllPresets(string resourceFolderPath)
        {
            LightingPresetFiles.Clear();
            WorldMapPresetFiles.Clear();
            WeatherPresetFiles.Clear();

            ScanLightingFolder(resourceFolderPath);
            ScanWeatherFolder(resourceFolderPath);
        }

        private void ScanLightingFolder(string resourceFolderPath)
        {
            string lightingFolderPath = Path.Combine(resourceFolderPath, "Lighting");

            if (!Directory.Exists(lightingFolderPath))
                return;

            string[] files = Directory.GetFiles(lightingFolderPath, "*.json", SearchOption.AllDirectories).OrderBy(path => path).ToArray();

            foreach (string filePath in files)
            {
                PresetFile preset = new PresetFile
                {
                    DisplayName = Path.GetRelativePath(lightingFolderPath, filePath),
                    FilePath = filePath
                };

                if (IsWorldMapPreset(filePath))
                    WorldMapPresetFiles.Add(preset);
                else
                    LightingPresetFiles.Add(preset);
            }
        }

        private void ScanWeatherFolder(string resourceFolderPath)
        {
            string weatherFolderPath = Path.Combine(resourceFolderPath, "weather");

            if (!Directory.Exists(weatherFolderPath))
                weatherFolderPath = Path.Combine(resourceFolderPath, "Weather");

            if (!Directory.Exists(weatherFolderPath))
                return;

            string[] files = Directory.GetFiles(weatherFolderPath, "*.json", SearchOption.AllDirectories).OrderBy(path => path).ToArray();

            foreach (string filePath in files)
            {
                WeatherPresetFiles.Add(new PresetFile
                {
                    DisplayName = Path.GetRelativePath(weatherFolderPath, filePath),
                    FilePath = filePath
                });
            }
        }

        private static bool IsWorldMapPreset(string filePath)
        {
            try
            {
                string jsonText = File.ReadAllText(filePath);
                JsonNode? parsedNode = JsonNode.Parse(jsonText);

                if (parsedNode is not JsonObject rootObject)
                    return false;

                string locationId = rootObject["locationId"]?.GetValue<string>() ?? "";
                string presetName = rootObject["presetName"]?.GetValue<string>() ?? "";

                return locationId.Equals("WorldMap", StringComparison.OrdinalIgnoreCase) ||
                       presetName.Equals("GlobalMap", StringComparison.OrdinalIgnoreCase);
            }
            catch
            {
                return false;
            }
        }

        private void RefreshVisiblePresetFiles()
        {
            if (VisiblePresetFiles == null)
                return;

            VisiblePresetFiles.Clear();

            ObservableCollection<PresetFile> source = CurrentMode switch
            {
                EditorMode.WorldMap => WorldMapPresetFiles,
                EditorMode.Weather => WeatherPresetFiles,
                _ => LightingPresetFiles
            };

            foreach (PresetFile preset in source)
                VisiblePresetFiles.Add(preset);

            SelectedPresetFile = null;
        }

        private void UpdateModeLabels()
        {
            switch (CurrentMode)
            {
                case EditorMode.WorldMap:
                    PresetListHeader = "World Map JSON:";
                    TableHeader = "Сезоны";
                    RightPanelHeader = "Редактор выбранного сезона";
                    break;

                case EditorMode.Weather:
                    PresetListHeader = "Weather JSON:";
                    TableHeader = "Часы погодного override";
                    RightPanelHeader = "Редактор выбранного часа погоды";
                    break;

                default:
                    PresetListHeader = "Lighting JSON:";
                    TableHeader = "Часы";
                    RightPanelHeader = "Редактор выбранного часа";
                    break;
            }
        }

        private void EditorMode_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            RefreshVisiblePresetFiles();
            UpdateModeLabels();
            ApplyModeVisibility();
        }

        private void PresetList_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (SelectedPresetFile == null)
                return;

            try
            {
                LoadJson(SelectedPresetFile.FilePath, CurrentMode);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка загрузки JSON:\n{ex.Message}", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void OpenJson_Click(object sender, RoutedEventArgs e)
        {
            OpenFileDialog dialog = new OpenFileDialog
            {
                Filter = "JSON files (*.json)|*.json|All files (*.*)|*.*",
                Title = "Открыть JSON"
            };

            if (dialog.ShowDialog() != true)
                return;

            try
            {
                LoadJson(dialog.FileName, DetectPresetMode(dialog.FileName));
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка загрузки JSON:\n{ex.Message}", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private EditorMode DetectPresetMode(string filePath)
        {
            try
            {
                string jsonText = File.ReadAllText(filePath);
                JsonNode? parsedNode = JsonNode.Parse(jsonText);

                if (parsedNode is not JsonObject rootObject)
                    return CurrentMode;

                string locationId = rootObject["locationId"]?.GetValue<string>() ?? "";
                string presetName = rootObject["presetName"]?.GetValue<string>() ?? "";
                string weatherType = rootObject["weatherType"]?.GetValue<string>() ?? "";
                string sourcePresetName = rootObject["sourcePresetName"]?.GetValue<string>() ?? "";

                if (!string.IsNullOrWhiteSpace(weatherType) || !string.IsNullOrWhiteSpace(sourcePresetName))
                    return EditorMode.Weather;

                if (locationId.Equals("WorldMap", StringComparison.OrdinalIgnoreCase) || presetName.Equals("GlobalMap", StringComparison.OrdinalIgnoreCase))
                    return EditorMode.WorldMap;

                return EditorMode.Lighting;
            }
            catch
            {
                return CurrentMode;
            }
        }

        private void LoadJson(string filePath, EditorMode mode)
        {
            _isLoadingFile = true;

            try
            {
                string jsonText = File.ReadAllText(filePath);
                JsonNode? parsedNode = JsonNode.Parse(jsonText);

                if (parsedNode is not JsonObject rootObject)
                    throw new Exception("Корень JSON должен быть объектом.");

                if (rootObject["hours"] is not JsonObject hoursObject)
                    throw new Exception("В JSON не найден объект hours.");

                _rootJson = rootObject;
                _currentFilePath = filePath;

                SelectedEditorMode = ModeToUiName(mode);

                if (mode == EditorMode.Lighting)
                {
                    SelectedGrassPresetName = ReadGrassPresetFromWeatherJson(rootObject);

                    if (!GrassPresetNames.Contains(SelectedGrassPresetName))
                        GrassPresetNames.Add(SelectedGrassPresetName);
                }

                if (mode == EditorMode.WorldMap)
                {
                    WorldMapSunAzimuth = ReadDouble(rootObject, "sun_azimuth");
                    WorldMapSunHeight = ReadDouble(rootObject, "sun_height");
                }

                if (mode == EditorMode.Weather)
                {
                    WeatherLocationId = ReadString(rootObject, "locationId");
                    WeatherPresetName = ReadString(rootObject, "presetName");
                    WeatherSourcePresetName = ReadString(rootObject, "sourcePresetName");
                    WeatherType = ReadString(rootObject, "weatherType");
                }

                Hours.Clear();

                int maxIndex = mode == EditorMode.WorldMap ? 3 : 23;

                for (int i = 0; i <= maxIndex; i++)
                {
                    string key = i.ToString(CultureInfo.InvariantCulture);

                    if (hoursObject[key] is not JsonObject hourObject)
                    {
                        Hours.Add(new WeatherHour
                        {
                            Hour = i,
                            IsMissingInJson = true
                        });

                        continue;
                    }

                    WeatherHour row = mode switch
                    {
                        EditorMode.WorldMap => WeatherHour.FromWorldMapJson(i, hourObject),
                        EditorMode.Weather => WeatherHour.FromWeatherOverrideJson(i, hourObject),
                        _ => WeatherHour.FromLightingJson(i, hourObject)
                    };

                    Hours.Add(row);
                }

                OpenedFiles.Clear();
                OpenedFiles.Add(Path.GetFileName(filePath));

                SubscribeToRows();
                SelectedHour = Hours.FirstOrDefault();
                ApplyModeVisibility();
                ClearDirty();
                RestartFileWatcher();
                UpdateMonitorStatus($"Файл загружен: {Path.GetFileName(filePath)}");
            }
            finally
            {
                _isLoadingFile = false;
            }
        }

        private static string ModeToUiName(EditorMode mode)
        {
            return mode switch
            {
                EditorMode.WorldMap => "World Map",
                EditorMode.Weather => "Weather",
                _ => "Lighting"
            };
        }

        private void SaveJson_Click(object sender, RoutedEventArgs e)
        {
            if (_currentFilePath == null)
            {
                SaveJsonAs_Click(sender, e);
                return;
            }

            try
            {
                SaveJson(_currentFilePath);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка сохранения JSON:\n{ex.Message}", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void SaveJsonAs_Click(object sender, RoutedEventArgs e)
        {
            SaveFileDialog dialog = new SaveFileDialog
            {
                Filter = "JSON files (*.json)|*.json|All files (*.*)|*.*",
                Title = "Сохранить JSON",
                FileName = _currentFilePath != null ? Path.GetFileName(_currentFilePath) : "preset.json"
            };

            if (dialog.ShowDialog() != true)
                return;

            try
            {
                SaveJson(dialog.FileName);
                _currentFilePath = dialog.FileName;
                RestartFileWatcher();

                OpenedFiles.Clear();
                OpenedFiles.Add(Path.GetFileName(dialog.FileName));
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка сохранения JSON:\n{ex.Message}", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void SaveJson(string filePath)
        {
            if (_rootJson == null)
                throw new Exception("JSON ещё не открыт.");

            ApplyRowsToJson();

            string backupPath = filePath + ".bak";

            _isSavingFromEditor = true;
            _ignoreWatcherUntil = DateTime.Now.AddSeconds(1.5);

            try
            {
                if (File.Exists(filePath))
                    File.Copy(filePath, backupPath, true);

                JsonSerializerOptions options = new JsonSerializerOptions
                {
                    WriteIndented = true
                };

                string outputJson = _rootJson.ToJsonString(options);
                File.WriteAllText(filePath, outputJson);
            }
            finally
            {
                _isSavingFromEditor = false;
            }

            ClearDirty();
            RestartFileWatcher();
            UpdateMonitorStatus($"Сохранено: {Path.GetFileName(filePath)}");

            MessageBox.Show($"JSON сохранён:\n{filePath}\n\nBackup:\n{backupPath}", "Сохранено", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void ApplyChanges_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                ApplyRowsToJson();
                MarkDirty();
                MessageBox.Show("Изменения применены во внутренний JSON.\nДля записи файла нажми «Сохранить».", "Готово", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка применения изменений:\n{ex.Message}", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void ApplyRowsToJson()
        {
            if (_rootJson == null)
                throw new Exception("JSON ещё не открыт.");

            if (CurrentMode == EditorMode.Lighting)
                _rootJson["grass_preset"] = GrassNameToWeatherJsonValue(SelectedGrassPresetName);

            if (CurrentMode == EditorMode.WorldMap)
            {
                _rootJson["sun_azimuth"] = WeatherHour.RoundNumber(WorldMapSunAzimuth);
                _rootJson["sun_height"] = WeatherHour.RoundNumber(WorldMapSunHeight);
            }

            if (CurrentMode == EditorMode.Weather)
            {
                _rootJson["locationId"] = WeatherLocationId;
                _rootJson["presetName"] = WeatherPresetName;
                _rootJson["sourcePresetName"] = WeatherSourcePresetName;
                _rootJson["weatherType"] = WeatherType;
            }

            if (_rootJson["hours"] is not JsonObject hoursObject)
                throw new Exception("В JSON не найден объект hours.");

            foreach (WeatherHour row in Hours)
            {
                string key = row.Hour.ToString(CultureInfo.InvariantCulture);

                if (hoursObject[key] is not JsonObject rowObject)
                {
                    rowObject = CreateEmptyRowObject(CurrentMode);
                    hoursObject[key] = rowObject;
                }

                switch (CurrentMode)
                {
                    case EditorMode.WorldMap:
                        row.ApplyToWorldMapJson(rowObject);
                        break;

                    case EditorMode.Weather:
                        row.ApplyToWeatherOverrideJson(rowObject);
                        break;

                    default:
                        row.ApplyToLightingJson(rowObject);
                        break;
                }
            }
        }

        private JsonObject CreateEmptyRowObject(EditorMode mode)
        {
            if (mode == EditorMode.Weather)
            {
                return new JsonObject
                {
                    ["ambient"] = new JsonObject
                    {
                        ["color"] = CreateArray(1.0, 1.0, 1.0),
                        ["intensity"] = 1.0
                    },
                    ["sun"] = new JsonObject
                    {
                        ["color"] = CreateArray(1.0, 1.0, 1.0),
                        ["intensity"] = 1.0
                    },
                    ["fog"] = new JsonObject
                    {
                        ["density"] = 0.0
                    },
                    ["shadow"] = new JsonObject
                    {
                        ["ao"] = 0.0
                    }
                };
            }

            if (mode == EditorMode.WorldMap)
            {
                return new JsonObject
                {
                    ["ambient"] = new JsonObject
                    {
                        ["color"] = CreateArray(1.0, 1.0, 1.0),
                        ["intensity"] = 1.0
                    },
                    ["bloom"] = new JsonObject
                    {
                        ["intensity"] = 0.1,
                        ["soft_treshold"] = 0.4,
                        ["treshold"] = 0.75
                    },
                    ["emission"] = 0.0,
                    ["exposure"] = 1.0,
                    ["fog"] = new JsonObject
                    {
                        ["color"] = CreateArray(0.0, 0.0, 0.0),
                        ["density"] = 0.0
                    },
                    ["hdr_texture"] = "",
                    ["point"] = new JsonObject(),
                    ["sea"] = new JsonObject
                    {
                        ["deep_color"] = CreateArray(0.0, 0.0, 0.0),
                        ["shallow_color"] = CreateArray(0.0, 0.0, 0.0)
                    },
                    ["shadow"] = new JsonObject
                    {
                        ["ao"] = 0.0
                    },
                    ["sun"] = new JsonObject
                    {
                        ["color"] = CreateArray(1.0, 1.0, 1.0),
                        ["intensity"] = 1.0
                    }
                };
            }

            return new JsonObject
            {
                ["ambient"] = new JsonObject
                {
                    ["color"] = CreateArray(1.0, 1.0, 1.0),
                    ["intensity"] = 1.0
                },
                ["bloom"] = new JsonObject
                {
                    ["intensity"] = 1.0,
                    ["soft_treshold"] = 0.5,
                    ["treshold"] = 3.0
                },
                ["emission"] = 0.0,
                ["exposure"] = 1.0,
                ["fog"] = new JsonObject
                {
                    ["color"] = CreateArray(0.0, 0.0, 0.0),
                    ["density"] = 0.002
                },
                ["hdr_texture"] = "",
                ["point"] = new JsonObject(),
                ["sea"] = new JsonObject
                {
                    ["color"] = CreateArray(0.0, 0.0, 0.0),
                    ["params"] = CreateArray(0.0, 0.0, 0.0),
                    ["sky"] = new JsonObject
                    {
                        ["color"] = CreateArray(0.0, 0.0, 0.0)
                    }
                },
                ["shadow"] = new JsonObject
                {
                    ["ao"] = 0.6
                },
                ["sun"] = new JsonObject
                {
                    ["color"] = CreateArray(1.0, 1.0, 1.0),
                    ["intensity"] = 1.0
                }
            };
        }

        private static JsonArray CreateArray(double a, double b, double c)
        {
            return new JsonArray(WeatherHour.RoundNumber(a), WeatherHour.RoundNumber(b), WeatherHour.RoundNumber(c));
        }

        private static string ReadGrassPresetFromWeatherJson(JsonObject rootObject)
        {
            string value = rootObject["grass_preset"]?.GetValue<string>() ?? "grass_default";

            if (string.IsNullOrWhiteSpace(value))
                return "default";

            value = value.Trim();

            if (value.StartsWith("grass_", StringComparison.OrdinalIgnoreCase))
                value = value.Substring("grass_".Length);

            return NormalizeGrassName(value);
        }

        private static string GrassNameToWeatherJsonValue(string cleanName)
        {
            string normalized = NormalizeGrassName(cleanName);
            return $"grass_{normalized}";
        }

        private static string NormalizeGrassName(string? name)
        {
            if (string.IsNullOrWhiteSpace(name))
                return "default";

            string normalized = name.Trim();

            if (normalized.StartsWith("grass_", StringComparison.OrdinalIgnoreCase))
                normalized = normalized.Substring("grass_".Length);

            if (string.IsNullOrWhiteSpace(normalized))
                return "default";

            return normalized;
        }

        private void RestartFileWatcher()
        {
            StopFileWatcher();

            if (!IsFileMonitoringEnabled)
            {
                UpdateMonitorStatus();
                return;
            }

            if (string.IsNullOrWhiteSpace(_currentFilePath) || !File.Exists(_currentFilePath))
            {
                UpdateMonitorStatus("Мониторинг включён, но файл не открыт");
                return;
            }

            string? directory = Path.GetDirectoryName(_currentFilePath);
            string fileName = Path.GetFileName(_currentFilePath);

            if (string.IsNullOrWhiteSpace(directory) || string.IsNullOrWhiteSpace(fileName))
            {
                UpdateMonitorStatus("Мониторинг включён, но путь файла некорректный");
                return;
            }

            _fileWatcher = new FileSystemWatcher(directory, fileName)
            {
                NotifyFilter = NotifyFilters.LastWrite | NotifyFilters.Size | NotifyFilters.FileName | NotifyFilters.CreationTime,
                IncludeSubdirectories = false,
                EnableRaisingEvents = true
            };

            _fileWatcher.Changed += WatchedFile_Changed;
            _fileWatcher.Created += WatchedFile_Changed;
            _fileWatcher.Renamed += WatchedFile_Renamed;

            UpdateMonitorStatus();
        }

        private void StopFileWatcher()
        {
            if (_fileWatcher == null)
                return;

            _fileWatcher.EnableRaisingEvents = false;
            _fileWatcher.Changed -= WatchedFile_Changed;
            _fileWatcher.Created -= WatchedFile_Changed;
            _fileWatcher.Renamed -= WatchedFile_Renamed;
            _fileWatcher.Dispose();
            _fileWatcher = null;
        }

        private void WatchedFile_Changed(object sender, FileSystemEventArgs e)
        {
            if (_isSavingFromEditor || DateTime.Now < _ignoreWatcherUntil)
                return;

            Dispatcher.Invoke(() =>
            {
                _reloadDebounceTimer?.Stop();
                _reloadDebounceTimer?.Start();
                UpdateMonitorStatus("Файл изменён снаружи, ожидание завершения записи...");
            });
        }

        private void WatchedFile_Renamed(object sender, RenamedEventArgs e)
        {
            WatchedFile_Changed(sender, e);
        }

        private void ReloadDebounceTimer_Tick(object? sender, EventArgs e)
        {
            _reloadDebounceTimer?.Stop();
            ReloadCurrentFileAfterExternalChange();
        }

        private void ReloadCurrentFileAfterExternalChange()
        {
            if (string.IsNullOrWhiteSpace(_currentFilePath) || !File.Exists(_currentFilePath))
                return;

            if (_hasUnsavedChanges)
            {
                if (SelectedAutoReloadMode == "Не обновлять, если есть несохранённые изменения")
                {
                    UpdateMonitorStatus("Файл изменён снаружи, но автообновление пропущено: есть несохранённые изменения");
                    return;
                }

                if (SelectedAutoReloadMode == "Спрашивать при конфликте")
                {
                    MessageBoxResult result = MessageBox.Show(
                        "Файл был изменён снаружи, но в редакторе есть несохранённые изменения.\n\nПерезагрузить файл и потерять текущие несохранённые правки?",
                        "Конфликт автообновления",
                        MessageBoxButton.YesNo,
                        MessageBoxImage.Warning);

                    if (result != MessageBoxResult.Yes)
                    {
                        UpdateMonitorStatus("Файл изменён снаружи, перезагрузка отменена пользователем");
                        return;
                    }
                }
            }

            TryReloadCurrentFileFromDisk();
        }

        private void TryReloadCurrentFileFromDisk()
        {
            if (string.IsNullOrWhiteSpace(_currentFilePath))
                return;

            Exception? lastError = null;

            for (int attempt = 0; attempt < 5; attempt++)
            {
                try
                {
                    EditorMode mode = DetectPresetMode(_currentFilePath);
                    LoadJson(_currentFilePath, mode);
                    UpdateMonitorStatus($"Файл автообновлён: {Path.GetFileName(_currentFilePath)}");
                    return;
                }
                catch (Exception ex)
                {
                    lastError = ex;
                    System.Threading.Thread.Sleep(120);
                }
            }

            UpdateMonitorStatus($"Ошибка автообновления: {lastError?.Message}");
        }

        private void ToggleTableExpand_Click(object sender, RoutedEventArgs e)
        {
            if (FindName("MainLayoutGrid") is not Grid layoutGrid)
                return;

            if (layoutGrid.ColumnDefinitions.Count < 5)
                return;

            if (!_isTableExpanded)
            {
                _savedLeftColumnWidth = layoutGrid.ColumnDefinitions[0].Width;
                _savedLeftSplitterColumnWidth = layoutGrid.ColumnDefinitions[1].Width;
                _savedCenterColumnWidth = layoutGrid.ColumnDefinitions[2].Width;
                _savedRightSplitterColumnWidth = layoutGrid.ColumnDefinitions[3].Width;
                _savedRightColumnWidth = layoutGrid.ColumnDefinitions[4].Width;

                _savedLeftColumnMinWidth = layoutGrid.ColumnDefinitions[0].MinWidth;
                _savedLeftSplitterColumnMinWidth = layoutGrid.ColumnDefinitions[1].MinWidth;
                _savedCenterColumnMinWidth = layoutGrid.ColumnDefinitions[2].MinWidth;
                _savedRightSplitterColumnMinWidth = layoutGrid.ColumnDefinitions[3].MinWidth;
                _savedRightColumnMinWidth = layoutGrid.ColumnDefinitions[4].MinWidth;

                layoutGrid.ColumnDefinitions[0].MinWidth = 0;
                layoutGrid.ColumnDefinitions[1].MinWidth = 0;
                layoutGrid.ColumnDefinitions[2].MinWidth = 0;
                layoutGrid.ColumnDefinitions[3].MinWidth = 0;
                layoutGrid.ColumnDefinitions[4].MinWidth = 0;

                SetElementVisibility("LeftPanelBorder", false);
                SetElementVisibility("LeftGridSplitter", false);
                SetElementVisibility("RightGridSplitter", false);
                SetElementVisibility("RightPanelBorder", false);

                layoutGrid.ColumnDefinitions[0].Width = new GridLength(0);
                layoutGrid.ColumnDefinitions[1].Width = new GridLength(0);
                layoutGrid.ColumnDefinitions[2].Width = new GridLength(1, GridUnitType.Star);
                layoutGrid.ColumnDefinitions[3].Width = new GridLength(0);
                layoutGrid.ColumnDefinitions[4].Width = new GridLength(0);

                _isTableExpanded = true;
                UpdateTableExpandButton();
            }
            else
            {
                layoutGrid.ColumnDefinitions[0].MinWidth = _savedLeftColumnMinWidth > 0 ? _savedLeftColumnMinWidth : 220;
                layoutGrid.ColumnDefinitions[1].MinWidth = _savedLeftSplitterColumnMinWidth;
                layoutGrid.ColumnDefinitions[2].MinWidth = _savedCenterColumnMinWidth > 0 ? _savedCenterColumnMinWidth : 420;
                layoutGrid.ColumnDefinitions[3].MinWidth = _savedRightSplitterColumnMinWidth;
                layoutGrid.ColumnDefinitions[4].MinWidth = _savedRightColumnMinWidth > 0 ? _savedRightColumnMinWidth : 300;

                layoutGrid.ColumnDefinitions[0].Width = _savedLeftColumnWidth.Value > 0 ? _savedLeftColumnWidth : new GridLength(280);
                layoutGrid.ColumnDefinitions[1].Width = _savedLeftSplitterColumnWidth.Value > 0 ? _savedLeftSplitterColumnWidth : new GridLength(6);
                layoutGrid.ColumnDefinitions[2].Width = _savedCenterColumnWidth.Value > 0 ? _savedCenterColumnWidth : new GridLength(1, GridUnitType.Star);
                layoutGrid.ColumnDefinitions[3].Width = _savedRightSplitterColumnWidth.Value > 0 ? _savedRightSplitterColumnWidth : new GridLength(6);
                layoutGrid.ColumnDefinitions[4].Width = _savedRightColumnWidth.Value > 0 ? _savedRightColumnWidth : new GridLength(400);

                SetElementVisibility("LeftPanelBorder", true);
                SetElementVisibility("LeftGridSplitter", true);
                SetElementVisibility("RightGridSplitter", true);
                SetElementVisibility("RightPanelBorder", true);

                _isTableExpanded = false;
                UpdateTableExpandButton();
                ApplyModeVisibility();
            }
        }

        private void UpdateTableExpandButton()
        {
            if (FindName("TableExpandButton") is not Button button)
                return;

            if (_isTableExpanded)
            {
                button.Content = "↩";
                button.ToolTip = "Вернуть панели";
            }
            else
            {
                button.Content = "⛶";
                button.ToolTip = "Развернуть таблицу";
            }
        }

        private void CopyParameter_Click(object sender, RoutedEventArgs e)
        {
            if (SelectedHour == null)
            {
                MessageBox.Show("Сначала выбери источник.", "Нет выбранного индекса", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            _copiedParameterMode = GetSelectedCopyMode();
            _copiedParameterSource = SelectedHour.Clone();

            MessageBox.Show($"Скопировано: {CopyParameterModeToLabel(_copiedParameterMode)} из индекса {SelectedHour.Hour}.", "Копирование параметра", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void PasteParameterToSelected_Click(object sender, RoutedEventArgs e)
        {
            if (_copiedParameterSource == null)
            {
                MessageBox.Show("Сначала скопируй параметр.", "Нет скопированного параметра", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            var selectedRows = HoursGrid.SelectedItems.OfType<WeatherHour>().ToList();

            if (selectedRows.Count == 0)
            {
                MessageBox.Show("Сначала выдели строки в таблице.", "Нет выделенных строк", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            foreach (WeatherHour target in selectedRows)
                target.CopyParameterFrom(_copiedParameterSource, _copiedParameterMode);

            HoursGrid.Items.Refresh();
        }

        private void PasteParameterToAll_Click(object sender, RoutedEventArgs e)
        {
            if (_copiedParameterSource == null)
            {
                MessageBox.Show("Сначала скопируй параметр.", "Нет скопированного параметра", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            MessageBoxResult result = MessageBox.Show($"Вставить параметр «{CopyParameterModeToLabel(_copiedParameterMode)}» во все строки?", "Подтверждение", MessageBoxButton.YesNo, MessageBoxImage.Question);

            if (result != MessageBoxResult.Yes)
                return;

            foreach (WeatherHour target in Hours)
                target.CopyParameterFrom(_copiedParameterSource, _copiedParameterMode);

            HoursGrid.Items.Refresh();
        }

        private CopyParameterMode GetSelectedCopyMode()
        {
            if (ParameterCopyComboBox.SelectedItem is not ComboBoxItem selectedItem)
                return CopyParameterMode.FullHour;

            string label = selectedItem.Content?.ToString() ?? "Full Hour";

            return label switch
            {
                "Full Hour" => CopyParameterMode.FullHour,
                "Sun Full Block" => CopyParameterMode.SunFullBlock,
                "Sun Color" => CopyParameterMode.SunColor,
                "Sun Intensity" => CopyParameterMode.SunIntensity,
                "Ambient Full Block" => CopyParameterMode.AmbientFullBlock,
                "Ambient Color" => CopyParameterMode.AmbientColor,
                "Ambient Intensity" => CopyParameterMode.AmbientIntensity,
                "Fog Full Block" => CopyParameterMode.FogFullBlock,
                "Fog Color" => CopyParameterMode.FogColor,
                "Fog Density" => CopyParameterMode.FogDensity,
                "Sea Full Block" => CopyParameterMode.SeaFullBlock,
                "Sea Color" => CopyParameterMode.SeaColor,
                "Sea Params" => CopyParameterMode.SeaParams,
                "Sea Sky Color" => CopyParameterMode.SeaSkyColor,
                "Bloom Full Block" => CopyParameterMode.BloomFullBlock,
                "Emission" => CopyParameterMode.Emission,
                "Exposure" => CopyParameterMode.Exposure,
                "Shadow AO" => CopyParameterMode.ShadowAO,
                "HDR Texture" => CopyParameterMode.HdrTexture,
                _ => CopyParameterMode.FullHour
            };
        }

        private static string CopyParameterModeToLabel(CopyParameterMode mode)
        {
            return mode.ToString();
        }

        private void PickSunColor_Click(object sender, RoutedEventArgs e) => PickColorForSelectedHour(ColorTarget.Sun);
        private void PickAmbientColor_Click(object sender, RoutedEventArgs e) => PickColorForSelectedHour(ColorTarget.Ambient);
        private void PickFogColor_Click(object sender, RoutedEventArgs e) => PickColorForSelectedHour(ColorTarget.Fog);
        private void PickSeaColor_Click(object sender, RoutedEventArgs e) => PickColorForSelectedHour(ColorTarget.Sea);
        private void PickSeaSkyColor_Click(object sender, RoutedEventArgs e) => PickColorForSelectedHour(ColorTarget.SeaSky);

        private void PickSunColorFromGrid_Click(object sender, RoutedEventArgs e) => PickColorFromGrid(sender, ColorTarget.Sun);
        private void PickAmbientColorFromGrid_Click(object sender, RoutedEventArgs e) => PickColorFromGrid(sender, ColorTarget.Ambient);
        private void PickFogColorFromGrid_Click(object sender, RoutedEventArgs e) => PickColorFromGrid(sender, ColorTarget.Fog);
        private void PickSeaColorFromGrid_Click(object sender, RoutedEventArgs e) => PickColorFromGrid(sender, ColorTarget.Sea);
        private void PickSeaSkyColorFromGrid_Click(object sender, RoutedEventArgs e) => PickColorFromGrid(sender, ColorTarget.SeaSky);

        private void PickColorFromGrid(object sender, ColorTarget target)
        {
            if (sender is not FrameworkElement element)
                return;

            if (element.DataContext is not WeatherHour hour)
                return;

            SelectedHour = hour;
            PickColorForHour(hour, target);
            HoursGrid.Items.Refresh();
        }

        private void PickColorForSelectedHour(ColorTarget target)
        {
            if (SelectedHour == null)
            {
                MessageBox.Show("Сначала выбери строку.", "Нет выбранной строки", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            PickColorForHour(SelectedHour, target);
            HoursGrid.Items.Refresh();
        }

        private void PickColorForHour(WeatherHour hour, ColorTarget target)
        {
            string currentText = target switch
            {
                ColorTarget.Sun => hour.SunColorText,
                ColorTarget.Ambient => hour.AmbientColorText,
                ColorTarget.Fog => hour.FogColorText,
                ColorTarget.Sea => hour.SeaColorText,
                ColorTarget.SeaSky => hour.SeaSkyColorText,
                _ => "0,0,0"
            };

            Drawing.Color startColor = WeatherHour.TextToDrawingColor(currentText);

            using Forms.ColorDialog dialog = new Forms.ColorDialog
            {
                FullOpen = true,
                Color = startColor,
                AnyColor = true,
                SolidColorOnly = false
            };

            if (dialog.ShowDialog() != Forms.DialogResult.OK)
                return;

            string newColorText = WeatherHour.DrawingColorToText(dialog.Color);

            switch (target)
            {
                case ColorTarget.Sun:
                    hour.SunColorText = newColorText;
                    break;
                case ColorTarget.Ambient:
                    hour.AmbientColorText = newColorText;
                    break;
                case ColorTarget.Fog:
                    hour.FogColorText = newColorText;
                    break;
                case ColorTarget.Sea:
                    hour.SeaColorText = newColorText;
                    break;
                case ColorTarget.SeaSky:
                    hour.SeaSkyColorText = newColorText;
                    break;
            }
        }

        private void CopyHour_Click(object sender, RoutedEventArgs e)
        {
            if (SelectedHour == null)
            {
                MessageBox.Show("Сначала выбери строку.", "Нет выбранной строки", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            _copiedHour = SelectedHour.Clone();

            MessageBox.Show($"Индекс {SelectedHour.Hour} скопирован.", "Копирование", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void PasteHourToAll_Click(object sender, RoutedEventArgs e)
        {
            if (_copiedHour == null && SelectedHour == null)
            {
                MessageBox.Show("Сначала выбери или скопируй строку.", "Нет источника", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            WeatherHour source = _copiedHour ?? SelectedHour!;

            MessageBoxResult result = MessageBox.Show($"Размножить параметры индекса {source.Hour} на все строки?", "Подтверждение", MessageBoxButton.YesNo, MessageBoxImage.Question);

            if (result != MessageBoxResult.Yes)
                return;

            foreach (WeatherHour target in Hours)
            {
                int originalHour = target.Hour;
                target.CopyValuesFrom(source);
                target.Hour = originalHour;
            }

            HoursGrid.Items.Refresh();
        }

        private void ValidatePreset_Click(object sender, RoutedEventArgs e)
        {
            if (_rootJson == null)
            {
                MessageBox.Show("JSON ещё не открыт.", "Проверка", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            int missingRows = Hours.Count(h => h.IsMissingInJson);

            MessageBox.Show($"Проверка завершена.\nРежим: {SelectedEditorMode}\nСтрок: {Hours.Count}\nОтсутствующих строк в исходном JSON: {missingRows}", "Проверка пресета", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void NormalizeHours_Click(object sender, RoutedEventArgs e)
        {
            if (_rootJson == null)
            {
                MessageBox.Show("JSON ещё не открыт.", "Ошибка", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            int targetCount = CurrentMode == EditorMode.WorldMap ? 4 : 24;

            MessageBoxResult result = MessageBox.Show($"Создать отсутствующие строки 0-{targetCount - 1} для режима {SelectedEditorMode}?", "Нормализация", MessageBoxButton.YesNo, MessageBoxImage.Question);

            if (result != MessageBoxResult.Yes)
                return;

            if (_rootJson["hours"] is not JsonObject hoursObject)
            {
                hoursObject = new JsonObject();
                _rootJson["hours"] = hoursObject;
            }

            if (CurrentMode == EditorMode.Lighting)
                _rootJson["grass_preset"] = GrassNameToWeatherJsonValue(SelectedGrassPresetName);

            for (int i = 0; i < targetCount; i++)
            {
                string key = i.ToString(CultureInfo.InvariantCulture);

                if (hoursObject[key] == null)
                    hoursObject[key] = CreateEmptyRowObject(CurrentMode);
            }

            if (_currentFilePath != null)
                LoadJson(_currentFilePath, CurrentMode);

            MessageBox.Show("Нормализация завершена.", "Готово", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void Exit_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private static double ReadDouble(JsonObject rootObject, string valueName)
        {
            return WeatherHour.RoundNumber(rootObject[valueName]?.GetValue<double>() ?? 0.0);
        }

        private static string ReadString(JsonObject rootObject, string valueName)
        {
            return rootObject[valueName]?.GetValue<string>() ?? "";
        }

        protected override void OnClosed(EventArgs e)
        {
            StopFileWatcher();
            base.OnClosed(e);
        }

        private void OnPropertyChanged(string propertyName)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }

    public enum EditorMode
    {
        Lighting,
        WorldMap,
        Weather
    }

    public class PresetFile
    {
        public string DisplayName { get; set; } = "";
        public string FilePath { get; set; } = "";
    }

    public enum ColorTarget
    {
        Sun,
        Ambient,
        Fog,
        Sea,
        SeaSky
    }

    public enum CopyParameterMode
    {
        FullHour,
        SunFullBlock,
        SunColor,
        SunIntensity,
        AmbientFullBlock,
        AmbientColor,
        AmbientIntensity,
        FogFullBlock,
        FogColor,
        FogDensity,
        SeaFullBlock,
        SeaColor,
        SeaParams,
        SeaSkyColor,
        BloomFullBlock,
        Emission,
        Exposure,
        ShadowAO,
        HdrTexture
    }

    public class WeatherHour : INotifyPropertyChanged
    {
        private int _hour;
        private string _sunColorText = "1,1,1";
        private double _sunIntensity;
        private string _ambientColorText = "1,1,1";
        private double _ambientIntensity;
        private string _fogColorText = "0,0,0";
        private double _fogDensity;
        private double _exposure;
        private double _shadowAO;
        private double _emission;
        private double _bloomIntensity;
        private double _bloomSoftThreshold;
        private double _bloomThreshold;
        private string _hdrTexture = "";
        private string _seaColorText = "0,0,0";
        private string _seaParamsText = "0,0,0";
        private string _seaSkyColorText = "0,0,0";

        public bool IsMissingInJson { get; set; }

        public int Hour
        {
            get => _hour;
            set
            {
                _hour = value;
                OnPropertyChanged(nameof(Hour));
            }
        }

        public string SunColorText
        {
            get => _sunColorText;
            set
            {
                _sunColorText = NormalizeColorText(value);
                OnPropertyChanged(nameof(SunColorText));
                OnPropertyChanged(nameof(SunBrush));
            }
        }

        public double SunIntensity
        {
            get => _sunIntensity;
            set
            {
                _sunIntensity = RoundNumber(value);
                OnPropertyChanged(nameof(SunIntensity));
            }
        }

        public string AmbientColorText
        {
            get => _ambientColorText;
            set
            {
                _ambientColorText = NormalizeColorText(value);
                OnPropertyChanged(nameof(AmbientColorText));
                OnPropertyChanged(nameof(AmbientBrush));
            }
        }

        public double AmbientIntensity
        {
            get => _ambientIntensity;
            set
            {
                _ambientIntensity = RoundNumber(value);
                OnPropertyChanged(nameof(AmbientIntensity));
            }
        }

        public string FogColorText
        {
            get => _fogColorText;
            set
            {
                _fogColorText = NormalizeColorText(value);
                OnPropertyChanged(nameof(FogColorText));
                OnPropertyChanged(nameof(FogBrush));
            }
        }

        public double FogDensity
        {
            get => _fogDensity;
            set
            {
                _fogDensity = RoundNumber(value);
                OnPropertyChanged(nameof(FogDensity));
            }
        }

        public double Exposure
        {
            get => _exposure;
            set
            {
                _exposure = RoundNumber(value);
                OnPropertyChanged(nameof(Exposure));
            }
        }

        public double ShadowAO
        {
            get => _shadowAO;
            set
            {
                _shadowAO = RoundNumber(value);
                OnPropertyChanged(nameof(ShadowAO));
            }
        }

        public double Emission
        {
            get => _emission;
            set
            {
                _emission = RoundNumber(value);
                OnPropertyChanged(nameof(Emission));
            }
        }

        public double BloomIntensity
        {
            get => _bloomIntensity;
            set
            {
                _bloomIntensity = RoundNumber(value);
                OnPropertyChanged(nameof(BloomIntensity));
            }
        }

        public double BloomSoftThreshold
        {
            get => _bloomSoftThreshold;
            set
            {
                _bloomSoftThreshold = RoundNumber(value);
                OnPropertyChanged(nameof(BloomSoftThreshold));
            }
        }

        public double BloomThreshold
        {
            get => _bloomThreshold;
            set
            {
                _bloomThreshold = RoundNumber(value);
                OnPropertyChanged(nameof(BloomThreshold));
            }
        }

        public string HdrTexture
        {
            get => _hdrTexture;
            set
            {
                _hdrTexture = value;
                OnPropertyChanged(nameof(HdrTexture));
            }
        }

        public string SeaColorText
        {
            get => _seaColorText;
            set
            {
                _seaColorText = NormalizeColorText(value);
                OnPropertyChanged(nameof(SeaColorText));
                OnPropertyChanged(nameof(SeaBrush));
            }
        }

        public string SeaParamsText
        {
            get => _seaParamsText;
            set
            {
                _seaParamsText = NormalizeVectorText(value);
                OnPropertyChanged(nameof(SeaParamsText));
            }
        }

        public string SeaSkyColorText
        {
            get => _seaSkyColorText;
            set
            {
                _seaSkyColorText = NormalizeColorText(value);
                OnPropertyChanged(nameof(SeaSkyColorText));
                OnPropertyChanged(nameof(SeaSkyBrush));
            }
        }

        public Brush SunBrush => TextToBrush(SunColorText);
        public Brush AmbientBrush => TextToBrush(AmbientColorText);
        public Brush FogBrush => TextToBrush(FogColorText);
        public Brush SeaBrush => TextToBrush(SeaColorText);
        public Brush SeaSkyBrush => TextToBrush(SeaSkyColorText);

        public event PropertyChangedEventHandler? PropertyChanged;

        public static WeatherHour FromLightingJson(int index, JsonObject hourObject)
        {
            return new WeatherHour
            {
                Hour = index,
                AmbientColorText = ReadArrayText(hourObject, "ambient", "color"),
                AmbientIntensity = ReadDouble(hourObject, "ambient", "intensity"),
                BloomIntensity = ReadDouble(hourObject, "bloom", "intensity"),
                BloomSoftThreshold = ReadDouble(hourObject, "bloom", "soft_treshold"),
                BloomThreshold = ReadDouble(hourObject, "bloom", "treshold"),
                Emission = ReadDouble(hourObject, "emission"),
                Exposure = ReadDouble(hourObject, "exposure"),
                FogColorText = ReadArrayText(hourObject, "fog", "color"),
                FogDensity = ReadDouble(hourObject, "fog", "density"),
                HdrTexture = ReadString(hourObject, "hdr_texture"),
                SeaColorText = ReadArrayText(hourObject, "sea", "color"),
                SeaParamsText = ReadArrayText(hourObject, "sea", "params"),
                SeaSkyColorText = ReadNestedArrayText(hourObject, "sea", "sky", "color"),
                ShadowAO = ReadDouble(hourObject, "shadow", "ao"),
                SunColorText = ReadArrayText(hourObject, "sun", "color"),
                SunIntensity = ReadDouble(hourObject, "sun", "intensity")
            };
        }

        public static WeatherHour FromWorldMapJson(int index, JsonObject rowObject)
        {
            return new WeatherHour
            {
                Hour = index,
                AmbientColorText = ReadArrayText(rowObject, "ambient", "color"),
                AmbientIntensity = ReadDouble(rowObject, "ambient", "intensity"),
                BloomIntensity = ReadDouble(rowObject, "bloom", "intensity"),
                BloomSoftThreshold = ReadDouble(rowObject, "bloom", "soft_treshold"),
                BloomThreshold = ReadDouble(rowObject, "bloom", "treshold"),
                Emission = ReadDouble(rowObject, "emission"),
                Exposure = ReadDouble(rowObject, "exposure"),
                FogColorText = ReadArrayText(rowObject, "fog", "color"),
                FogDensity = ReadDouble(rowObject, "fog", "density"),
                HdrTexture = ReadString(rowObject, "hdr_texture"),
                SeaColorText = ReadArrayText(rowObject, "sea", "deep_color"),
                SeaParamsText = "0,0,0",
                SeaSkyColorText = ReadArrayText(rowObject, "sea", "shallow_color"),
                ShadowAO = ReadDouble(rowObject, "shadow", "ao"),
                SunColorText = ReadArrayText(rowObject, "sun", "color"),
                SunIntensity = ReadDouble(rowObject, "sun", "intensity")
            };
        }

        public static WeatherHour FromWeatherOverrideJson(int index, JsonObject rowObject)
        {
            return new WeatherHour
            {
                Hour = index,
                AmbientColorText = ReadArrayText(rowObject, "ambient", "color"),
                AmbientIntensity = ReadDouble(rowObject, "ambient", "intensity"),
                SunColorText = ReadArrayText(rowObject, "sun", "color"),
                SunIntensity = ReadDouble(rowObject, "sun", "intensity"),
                FogColorText = "0,0,0",
                FogDensity = ReadDouble(rowObject, "fog", "density"),
                ShadowAO = ReadDouble(rowObject, "shadow", "ao"),
                BloomIntensity = 0.0,
                BloomSoftThreshold = 0.0,
                BloomThreshold = 0.0,
                Emission = 0.0,
                Exposure = 0.0,
                HdrTexture = "",
                SeaColorText = "0,0,0",
                SeaParamsText = "0,0,0",
                SeaSkyColorText = "0,0,0"
            };
        }

        public void ApplyToLightingJson(JsonObject hourObject)
        {
            SetArray(hourObject, "ambient", "color", AmbientColorText);
            SetDouble(hourObject, "ambient", "intensity", AmbientIntensity);
            SetDouble(hourObject, "bloom", "intensity", BloomIntensity);
            SetDouble(hourObject, "bloom", "soft_treshold", BloomSoftThreshold);
            SetDouble(hourObject, "bloom", "treshold", BloomThreshold);
            hourObject["emission"] = RoundNumber(Emission);
            hourObject["exposure"] = RoundNumber(Exposure);
            SetArray(hourObject, "fog", "color", FogColorText);
            SetDouble(hourObject, "fog", "density", FogDensity);
            hourObject["hdr_texture"] = HdrTexture;
            SetArray(hourObject, "sea", "color", SeaColorText);
            SetArray(hourObject, "sea", "params", SeaParamsText);
            SetNestedArray(hourObject, "sea", "sky", "color", SeaSkyColorText);
            SetDouble(hourObject, "shadow", "ao", ShadowAO);
            SetArray(hourObject, "sun", "color", SunColorText);
            SetDouble(hourObject, "sun", "intensity", SunIntensity);
        }

        public void ApplyToWorldMapJson(JsonObject rowObject)
        {
            SetArray(rowObject, "ambient", "color", AmbientColorText);
            SetDouble(rowObject, "ambient", "intensity", AmbientIntensity);
            SetDouble(rowObject, "bloom", "intensity", BloomIntensity);
            SetDouble(rowObject, "bloom", "soft_treshold", BloomSoftThreshold);
            SetDouble(rowObject, "bloom", "treshold", BloomThreshold);
            rowObject["emission"] = RoundNumber(Emission);
            rowObject["exposure"] = RoundNumber(Exposure);
            SetArray(rowObject, "fog", "color", FogColorText);
            SetDouble(rowObject, "fog", "density", FogDensity);
            rowObject["hdr_texture"] = HdrTexture;
            SetArray(rowObject, "sea", "deep_color", SeaColorText);
            SetArray(rowObject, "sea", "shallow_color", SeaSkyColorText);
            SetDouble(rowObject, "shadow", "ao", ShadowAO);
            SetArray(rowObject, "sun", "color", SunColorText);
            SetDouble(rowObject, "sun", "intensity", SunIntensity);
        }

        public void ApplyToWeatherOverrideJson(JsonObject rowObject)
        {
            SetArray(rowObject, "ambient", "color", AmbientColorText);
            SetDouble(rowObject, "ambient", "intensity", AmbientIntensity);
            SetArray(rowObject, "sun", "color", SunColorText);
            SetDouble(rowObject, "sun", "intensity", SunIntensity);
            JsonObject fogObject = GetOrCreateObject(rowObject, "fog");
            fogObject["density"] = RoundNumber(FogDensity);
            SetDouble(rowObject, "shadow", "ao", ShadowAO);
        }

        public WeatherHour Clone()
        {
            return new WeatherHour
            {
                Hour = Hour,
                SunColorText = SunColorText,
                SunIntensity = SunIntensity,
                AmbientColorText = AmbientColorText,
                AmbientIntensity = AmbientIntensity,
                FogColorText = FogColorText,
                FogDensity = FogDensity,
                Exposure = Exposure,
                ShadowAO = ShadowAO,
                Emission = Emission,
                BloomIntensity = BloomIntensity,
                BloomSoftThreshold = BloomSoftThreshold,
                BloomThreshold = BloomThreshold,
                HdrTexture = HdrTexture,
                SeaColorText = SeaColorText,
                SeaParamsText = SeaParamsText,
                SeaSkyColorText = SeaSkyColorText,
                IsMissingInJson = IsMissingInJson
            };
        }

        public void CopyValuesFrom(WeatherHour source)
        {
            SunColorText = source.SunColorText;
            SunIntensity = source.SunIntensity;
            AmbientColorText = source.AmbientColorText;
            AmbientIntensity = source.AmbientIntensity;
            FogColorText = source.FogColorText;
            FogDensity = source.FogDensity;
            Exposure = source.Exposure;
            ShadowAO = source.ShadowAO;
            Emission = source.Emission;
            BloomIntensity = source.BloomIntensity;
            BloomSoftThreshold = source.BloomSoftThreshold;
            BloomThreshold = source.BloomThreshold;
            HdrTexture = source.HdrTexture;
            SeaColorText = source.SeaColorText;
            SeaParamsText = source.SeaParamsText;
            SeaSkyColorText = source.SeaSkyColorText;
        }

        public void CopyParameterFrom(WeatherHour source, CopyParameterMode mode)
        {
            switch (mode)
            {
                case CopyParameterMode.FullHour:
                    CopyValuesFrom(source);
                    break;
                case CopyParameterMode.SunFullBlock:
                    SunColorText = source.SunColorText;
                    SunIntensity = source.SunIntensity;
                    break;
                case CopyParameterMode.SunColor:
                    SunColorText = source.SunColorText;
                    break;
                case CopyParameterMode.SunIntensity:
                    SunIntensity = source.SunIntensity;
                    break;
                case CopyParameterMode.AmbientFullBlock:
                    AmbientColorText = source.AmbientColorText;
                    AmbientIntensity = source.AmbientIntensity;
                    break;
                case CopyParameterMode.AmbientColor:
                    AmbientColorText = source.AmbientColorText;
                    break;
                case CopyParameterMode.AmbientIntensity:
                    AmbientIntensity = source.AmbientIntensity;
                    break;
                case CopyParameterMode.FogFullBlock:
                    FogColorText = source.FogColorText;
                    FogDensity = source.FogDensity;
                    break;
                case CopyParameterMode.FogColor:
                    FogColorText = source.FogColorText;
                    break;
                case CopyParameterMode.FogDensity:
                    FogDensity = source.FogDensity;
                    break;
                case CopyParameterMode.SeaFullBlock:
                    SeaColorText = source.SeaColorText;
                    SeaParamsText = source.SeaParamsText;
                    SeaSkyColorText = source.SeaSkyColorText;
                    break;
                case CopyParameterMode.SeaColor:
                    SeaColorText = source.SeaColorText;
                    break;
                case CopyParameterMode.SeaParams:
                    SeaParamsText = source.SeaParamsText;
                    break;
                case CopyParameterMode.SeaSkyColor:
                    SeaSkyColorText = source.SeaSkyColorText;
                    break;
                case CopyParameterMode.BloomFullBlock:
                    BloomIntensity = source.BloomIntensity;
                    BloomSoftThreshold = source.BloomSoftThreshold;
                    BloomThreshold = source.BloomThreshold;
                    break;
                case CopyParameterMode.Emission:
                    Emission = source.Emission;
                    break;
                case CopyParameterMode.Exposure:
                    Exposure = source.Exposure;
                    break;
                case CopyParameterMode.ShadowAO:
                    ShadowAO = source.ShadowAO;
                    break;
                case CopyParameterMode.HdrTexture:
                    HdrTexture = source.HdrTexture;
                    break;
            }
        }

        public static Drawing.Color TextToDrawingColor(string valueText)
        {
            (double r, double g, double b) = ParseTriple(valueText);
            return Drawing.Color.FromArgb(ToByte(r), ToByte(g), ToByte(b));
        }

        public static string DrawingColorToText(Drawing.Color color)
        {
            return TripleToText(color.R / 255.0, color.G / 255.0, color.B / 255.0);
        }

        public static double RoundNumber(double value)
        {
            return Math.Round(value, 6, MidpointRounding.AwayFromZero);
        }

        private static Brush TextToBrush(string valueText)
        {
            (double r, double g, double b) = ParseTriple(valueText);
            return new SolidColorBrush(Color.FromRgb((byte)ToByte(r), (byte)ToByte(g), (byte)ToByte(b)));
        }

        private static int ToByte(double value)
        {
            double clamped = Math.Clamp(value, 0.0, 1.0);
            return (int)Math.Round(clamped * 255.0);
        }

        private static string NormalizeColorText(string valueText)
        {
            (double r, double g, double b) = ParseTriple(valueText);
            return TripleToText(r, g, b);
        }

        private static string NormalizeVectorText(string valueText)
        {
            (double r, double g, double b) = ParseTriple(valueText);
            return TripleToText(r, g, b);
        }

        private static string TripleToText(double a, double b, double c)
        {
            return string.Join(",", RoundNumber(a).ToString("0.######", CultureInfo.InvariantCulture), RoundNumber(b).ToString("0.######", CultureInfo.InvariantCulture), RoundNumber(c).ToString("0.######", CultureInfo.InvariantCulture));
        }

        private static (double, double, double) ParseTriple(string valueText)
        {
            string[] parts = valueText.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
            double a = parts.Length > 0 ? ParseDouble(parts[0]) : 0.0;
            double b = parts.Length > 1 ? ParseDouble(parts[1]) : 0.0;
            double c = parts.Length > 2 ? ParseDouble(parts[2]) : 0.0;
            return (RoundNumber(a), RoundNumber(b), RoundNumber(c));
        }

        private static string ReadArrayText(JsonObject rootObject, string objectName, string arrayName)
        {
            if (rootObject[objectName] is not JsonObject childObject)
                return "0,0,0";
            if (childObject[arrayName] is not JsonArray array)
                return "0,0,0";
            return ArrayToText(array);
        }

        private static string ReadNestedArrayText(JsonObject rootObject, string objectName, string nestedObjectName, string arrayName)
        {
            if (rootObject[objectName] is not JsonObject childObject)
                return "0,0,0";
            if (childObject[nestedObjectName] is not JsonObject nestedObject)
                return "0,0,0";
            if (nestedObject[arrayName] is not JsonArray array)
                return "0,0,0";
            return ArrayToText(array);
        }

        private static string ArrayToText(JsonArray array)
        {
            return TripleToText(ReadArrayDouble(array, 0), ReadArrayDouble(array, 1), ReadArrayDouble(array, 2));
        }

        private static double ReadArrayDouble(JsonArray array, int index)
        {
            if (index < 0 || index >= array.Count)
                return 0.0;
            return RoundNumber(array[index]?.GetValue<double>() ?? 0.0);
        }

        private static double ReadDouble(JsonObject rootObject, string valueName)
        {
            return RoundNumber(rootObject[valueName]?.GetValue<double>() ?? 0.0);
        }

        private static double ReadDouble(JsonObject rootObject, string objectName, string valueName)
        {
            if (rootObject[objectName] is not JsonObject childObject)
                return 0.0;
            return RoundNumber(childObject[valueName]?.GetValue<double>() ?? 0.0);
        }

        private static string ReadString(JsonObject rootObject, string valueName)
        {
            return rootObject[valueName]?.GetValue<string>() ?? "";
        }

        private static void SetDouble(JsonObject rootObject, string objectName, string valueName, double value)
        {
            JsonObject childObject = GetOrCreateObject(rootObject, objectName);
            childObject[valueName] = RoundNumber(value);
        }

        private static void SetArray(JsonObject rootObject, string objectName, string arrayName, string valueText)
        {
            JsonObject childObject = GetOrCreateObject(rootObject, objectName);
            childObject[arrayName] = ParseArray(valueText);
        }

        private static void SetNestedArray(JsonObject rootObject, string objectName, string nestedObjectName, string arrayName, string valueText)
        {
            JsonObject childObject = GetOrCreateObject(rootObject, objectName);
            JsonObject nestedObject = GetOrCreateObject(childObject, nestedObjectName);
            nestedObject[arrayName] = ParseArray(valueText);
        }

        private static JsonObject GetOrCreateObject(JsonObject rootObject, string objectName)
        {
            if (rootObject[objectName] is JsonObject existingObject)
                return existingObject;
            JsonObject newObject = new JsonObject();
            rootObject[objectName] = newObject;
            return newObject;
        }

        private static JsonArray ParseArray(string valueText)
        {
            (double a, double b, double c) = ParseTriple(valueText);
            return new JsonArray(RoundNumber(a), RoundNumber(b), RoundNumber(c));
        }

        private static double ParseDouble(string valueText)
        {
            if (double.TryParse(valueText, NumberStyles.Float, CultureInfo.InvariantCulture, out double result))
                return RoundNumber(result);
            if (double.TryParse(valueText, NumberStyles.Float, CultureInfo.CurrentCulture, out result))
                return RoundNumber(result);
            return 0.0;
        }

        private void OnPropertyChanged(string propertyName)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }
}
