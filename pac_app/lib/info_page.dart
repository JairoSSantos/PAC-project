import 'dart:io';
import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:gallery_saver/gallery_saver.dart';
import 'package:photo_view/photo_view.dart';
import 'package:http/http.dart' as http;
import 'package:pac_app/config.dart';
import 'package:path_provider/path_provider.dart';
import 'package:flutter_speed_dial/flutter_speed_dial.dart';
import 'package:image_picker/image_picker.dart';
import 'package:image_cropper/image_cropper.dart';
import 'package:open_filex/open_filex.dart';
import 'package:permission_handler/permission_handler.dart';

const pow2Unicode = '\u00B2';

Future<String> getUrl() async {
  return 'http://${await Default.ipAddress}:${await Default.port}'; //prefs.getStr('ip_address') 'http://192.168.15.146:5000';
}

Map<String, String> getResultLabels({bool? id}) => {
  if (id != null && id) 'id': 'Id',
  'area': 'Área (${Default.unit}$pow2Unicode)',
  'extent': 'Largura (${Default.unit})',
};

Future<Map> sendImage(String path, {String? route, Map<String, String>? fields}) async {
  final file = await http.MultipartFile.fromPath('image', path);
  final url = await getUrl();
  final request = http.MultipartRequest('POST', Uri.parse('$url/${(route ?? '')}'));
  request.files.add(file);
  request.fields.addAll(fields ?? {});
  final response = await http.Response.fromStream(await request.send());
  return json.decode(response.body.toString());
}

num sum(Iterable<num> sample) => sample.reduce((a, b) => a + b);

Map<String, String> statistics(Iterable<num> sample){
  final mean = sum(sample)/sample.length;
  final std = math.sqrt(sum(sample.map((x) => math.pow(x - mean, 2)))/sample.length);
  return {
    'Média': mean.toStringAsFixed(Default.precision),
    'Desvio padrão': std.toStringAsFixed(Default.precision),
    'Desvio relativo (%)': (100*std/mean).toStringAsFixed(Default.precision)
  };
}

class Result {
  final String imagePath;

  ImageProvider? imgProvider;
  MemoryImage? segProvider;
  Image? img; 
  Image? seg;
  num area=0; 
  num scale= 0;
  Size dims = Size.zero;
  List<PyFunction> postProcess = [];
  bool viewSegState = true;
  int? id;

  Result({required this.imagePath}){
    final imgFile = File(imagePath);
    img = Image.file(imgFile, fit: BoxFit.contain);
    imgProvider = FileImage(imgFile);
  }

  Future<void> determinate() async {
    final response = await sendImage(imagePath, 
      fields:{
        'post_process': json.encode({
          for (final PyFunction pyfunc in postProcess) 
          pyfunc.name: pyfunc.asMap()
        })
      }
    );
    area = response['area'];
    scale = response['scale'];
    dims = Default.imageSize * math.sqrt(response['scale']);
    final segData = const Base64Decoder().convert(response['segmentation'].split(',').last);
    seg = Image.memory(segData, fit: BoxFit.contain);
    segProvider = MemoryImage(segData);
    viewSegState = true;
  }

  void changeViewState({bool? value}) => viewSegState= (value != null) ? value : !viewSegState;

  // String get extent => '${} \u00D7 ${dims.height.round()}';

  Map<String, String> get result => {
    'id': id.toString(),
    'area': area.toStringAsFixed(Default.precision),
    'extent': dims.width.round().toString()
  };

  dynamic get currentProvider => (viewSegState && segProvider != null) ? segProvider : imgProvider;

  dynamic get currentImage => (viewSegState && seg != null) ? seg : img;
}

class Root extends StatefulWidget {
  final String originalPath;
  final String initialPath;
  final String defaultSampleName;

  const Root({super.key, required this.originalPath, required this.initialPath, required this.defaultSampleName});

  @override
  State<Root> createState() => _RootState();
}

class _RootState extends State<Root> {

  late String _originalPath;
  late List<Result> _results;
  late bool _isLoading;
  late List<String> _headings;
  late int _currentPage;
  late bool _showPostProcess;
  late List<String> _comments;
  late bool _showComments;
  late String _sampleName;

  // ignore: non_constant_identifier_names
  Iterable<num> get Areas => _results.map((result) => result.area);

  void setLoading(value) => setState(() => _isLoading=value);

  Future<String> saveImage({required String path}) async {
    setLoading(true);
    final success = await GallerySaver.saveImage(
      path, 
      albumName: 'PAC'
    );
    setLoading(false);
    return (success ?? false) ? 'Imagem salva!' : 'Erro ao salvar imagem!';
  }

  void showQuickMessage(BuildContext context, String message){
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message))
    );
  }

  Future<dynamic> showAlertMessage(
    BuildContext context, 
    String title, 
    String message, 
    {Map<String, dynamic> options= const {'ok': null}}
  ) async {
    dynamic output;
    await showDialog(
      context: context, 
      builder: (_) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          for (final MapEntry element in options.entries)
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              output = element.value;
            }, 
            child: Text(element.key)
          )
        ]
      )
    );
    return output;
  }

  void addComment(BuildContext context, {String? content, String? replace}) => showDialog(
    context: context, 
    builder: (_) => AlertDialog(
      title: const Text('Adicionar comentário'),
      content: TextField(
        // expands: true,
        maxLines: 4,
        controller: TextEditingController(text: replace),
        decoration: const InputDecoration(
          border: UnderlineInputBorder(),
          labelText: 'Conteúdo',
        ),
        onChanged: ((value) => content=value),
      ),
      actions: [
          TextButton(
            onPressed: () => Navigator.pop(context), 
            child: const Text('Cancelar')
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              if (replace != null){
                _comments.insert(_comments.indexOf(replace), content ?? replace);
                _comments.remove(replace);
              } else {
                _comments.add(content!);
              }
            }, 
            child: const Text('Salvar')
          )
        ],
    )
  );

  void setDefaultParam(BuildContext context, String paramName){
    var currentValue = Default.getParamByName(paramName);
    showDialog(
      context: context, 
      builder: (_) => AlertDialog(
        title: Text('Alterar ${Default.getParamLabel(paramName)}'),
        content: TextField(
          decoration: InputDecoration(
            border: const UnderlineInputBorder(),
            hintText: currentValue.toString()
          ),
          onChanged: (newValue) => currentValue=newValue
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context), 
            child: const Text('Cancelar')
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              setState(() => Default.setParamByName(paramName, currentValue));
            }, 
            child: const Text('Salvar')
          )
        ],
      )
    );
  }

  void addNewResult(Result newResult){
    newResult.id = _results.length + 1;
    _results.add(newResult);
  }

  Future<void> preProcess(String path) async {
    CroppedFile? croppedImage = await ImageCropper().cropImage(
      sourcePath: path,
      aspectRatio: const CropAspectRatio(ratioX: 1, ratioY: 1)
    );
    if (croppedImage != null) {
      final newResult = Result(imagePath: croppedImage.path);
      await newResult.determinate().whenComplete(() => addNewResult(newResult));
    }
  }

  Future<void> pickImageAndResult(ImageSource source) async {
    XFile? imageXFile = await ImagePicker().pickImage(source: source);
    if (imageXFile != null){
      _originalPath = imageXFile.path;
      preProcess(imageXFile.path);
    }
  }

  List<Widget> get postProcessingTab => [
    for (final PyFunction pyfunc in _results[_currentPage].postProcess)
    ListTile(
      title: Text(pyfunc.label),
      subtitle: Column(
        children: [
          for (final PyParam param in pyfunc.params)
          Row(
            children:[
              Text(param.label),
              Slider(
                min: param.min.toDouble(),
                max: param.max.toDouble(),
                value: param.value.toDouble(),
                onChanged: (v) => setState(() => param.value=v.round()),
              ),
              IconButton(
                onPressed: () => setState((){
                  _results[_currentPage].postProcess.remove(pyfunc);
                }), 
                icon: const Icon(Icons.close)
              )
            ]
          )
        ]
      )
    ),
    DropdownButton(
      hint: const Text('Adicionar pós-processamento'),
      items: [
        for (final Morphology morphology in Morphology.values)
        DropdownMenuItem(
          value: morphology.pyFunc(),
          child: Text(morphology.label)
        )
      ], 
      onChanged: (pyfunc) => setState(() => _results[_currentPage].postProcess.add(pyfunc!))
    ),
    if (_results[_currentPage].postProcess.isNotEmpty)
    TextButton(
      onPressed: () {
        _showPostProcess = false;
        setLoading(true);
        _results[_currentPage].determinate().then(
          (_) => setLoading(false),
          onError: (e) => showAlertMessage(context, 'Erro ao determinar a área da amostra', e.toString()),
        );
      }, 
      child: const Text('Aplicar')
    )
  ];

  List<Widget> get commentsTab => [
    ..._comments.map((comment) => Card(child: ListTile(
      title: Text(comment),
      subtitle: Row(children: [
        IconButton(onPressed: () => setState(() => _comments.remove(comment)), icon: const Icon(Icons.delete_outline)),
        IconButton(onPressed: (){
          addComment(context, content: comment, replace: comment);
          setState(() {});
        }, icon: const Icon(Icons.edit_outlined))
      ]),
    ))),
    IconButton(
      onPressed: () => setState(() => addComment(context)), 
      icon: const Icon(Icons.add_comment)
    )
  ];

  List<Widget> get resultsSummaryTab => [
    const Text(
      'Resultados',
      style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)
    ),
    Padding(
      padding: const EdgeInsets.all(10),
      child: Table(
        border: TableBorder.all(),
        columnWidths: const {
          0: FractionColumnWidth(0.15)
        },
        children: [
          TableRow(
            decoration: BoxDecoration(color: Colors.grey[700]),
            children: _headings.map((value) => TableCell(
                child: Text(
                  value, 
                  textAlign: TextAlign.center, 
                  style: const TextStyle(
                    fontSize: 14, 
                    fontWeight: FontWeight.bold, 
                    color: Colors.white
                  )
                )
              )
            ).toList(),
          ),
          for (int index=0; index < _results.length; index++)
          TableRow(
            // decoration: BoxDecoration(color: (_results.length > 1 &&_currentPage == index) ? Colors.blue[100] : Colors.white),
            children: _results[index].result.values.map(
              (value) => TableCell(child: Text(value, textAlign: TextAlign.center))
            ).toList()
          )
        ]
      )
    ),
    if (_results.length > 1)
    Padding(
      padding: const EdgeInsets.fromLTRB(10, 0, 10, 10),
      child: Table(
        border: TableBorder.all(),
        columnWidths: const {
          0: FractionColumnWidth(0.35)
        },
        children: [
          TableRow(
            decoration: BoxDecoration(color: Colors.grey[700]),
            children: [
              const TableCell(child: Text('')),
              TableCell(
                child: Text(
                  'Área (${Default.unit}\u00B2)',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14, 
                    fontWeight: FontWeight.bold
                  ),
                )
              )
            ] 
          ),
          for (MapEntry element in statistics(Areas).entries)
          TableRow(
            children: [
              TableCell(
                child: Container(
                  alignment: Alignment.center,
                  color: Colors.grey[700],
                  child: Text(
                    element.key,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14, 
                      fontWeight: FontWeight.bold
                    ),
                  )
                )
              ),
              TableCell(
                child: Text(
                  element.value, 
                  textAlign: TextAlign.center
                )
              )
            ]
          ),
        ]
      )
    )
  ];

  void setSampleName(){
    var newSampleName = Default.sampleName;
    showDialog(
      context: context, 
      builder: (_) => AlertDialog(
        title: const Text('Adicione um nome à amostra'),
        content: TextField(
          decoration: InputDecoration(
            border: const UnderlineInputBorder(),
            hintText: newSampleName
          ),
          onChanged: (newValue) => newSampleName=newValue
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context), 
            child: const Text('Cancelar')
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              setState(() => _sampleName=newSampleName);
            }, 
            child: const Text('Salvar')
          )
        ],
      )
    );
  }

  Future<void> getReport() async {
    final allResults = getResultLabels(id: true).map(
      (key, label) => MapEntry(label, _results.map((element) => element.result[key]).toList())
    );
    // final images = Map.fromEntries(_results.map((result) => MapEntry(result.id.toString(), base64Encode(result.segProvider!.bytes))));
    final summary = {'#': [getResultLabels()['area']], ...statistics(_results.map((result) => result.area)).map((key, value) => MapEntry(key, [value]))};
    final url = await getUrl();
    final request = http.MultipartRequest('POST', Uri.parse('$url/result'));
    final images = Map.fromEntries(_results.map((result) => MapEntry(result.id.toString(), base64Encode(result.segProvider!.bytes))));
    request.fields.addAll({
      'sample_name': _sampleName,
      'results': jsonEncode(allResults),
      'summary': jsonEncode(summary),
      'area_label': getResultLabels()['area']!,
      'images': jsonEncode(images),
      'comments': jsonEncode(Map.fromIterables(_comments, List.filled(_comments.length, '')))
    });

    final response = await http.Response.fromStream(await request.send());
    final fileBytes = const Base64Decoder().convert(json.decode(response.body.toString())['report'].split(',').last);
    final status = await Permission.storage.status;
    if (!status.isGranted) {
      await Permission.storage.request();
    } 
    final path = '${(await getApplicationDocumentsDirectory()).path}/$_sampleName.pdf';
    File(path).writeAsBytes(fileBytes).whenComplete(() => OpenFilex.open(path).whenComplete(() => showQuickMessage(context, 'Relatório salvo!')));
  }

  @override
  void initState() {
    super.initState();

    _originalPath = widget.originalPath;
    _results = [];
    setLoading(true);
    final initialResult = Result(imagePath: widget.initialPath);
    initialResult.determinate().then(
      (_) {
        addNewResult(initialResult);
        setLoading(false);
      },
      onError: (e) => showAlertMessage(context, 'Erro ao determinar a área da amostra', e.toString()),
    );
    _currentPage = 0;

    _headings = [];
    _showPostProcess = false;

    _comments = [];
    _showComments = false;
    _sampleName = widget.defaultSampleName;
  }

  @override
  Widget build(BuildContext context) {
    _headings = [
      'Id',
      'Área (${Default.unit}$pow2Unicode)',  
      'Tamanho (${Default.unit})'
    ];
    final PageController controller = PageController(viewportFraction: 0.85);
    final screenSize = MediaQuery.of(context).size;

    return Scaffold(
      backgroundColor: Colors.grey[250],
      appBar: AppBar(
        title: Text(_sampleName),
        leading: IconButton(
          icon: const Icon(Icons.keyboard_backspace),
          onPressed: () => showAlertMessage(
            context, 
            'Deseja voltar à tela inicial?', 
            'Se não forem salvos, os resultados obtidos serão perdidos!', 
            options: {'Cancelar': false, 'Ok': true}
          ).then((ok) {
            if (ok) Navigator.of(context).popUntil(ModalRoute.withName('/'));
          }),
        ),
        actions: [
          if (_isLoading) Transform.scale(
            scaleX: 0.6,
            scaleY: 0.4,
            child: const CircularProgressIndicator(color: Colors.white)
          ),
          IconButton(
            onPressed: () => setSampleName(), 
            icon: const Icon(Icons.edit)
          ),
          IconButton(
            onPressed: () {
              setLoading(true);
              getReport().whenComplete(() => setLoading(false));
            }, 
            icon: const Icon(Icons.feed_outlined)
          ),
          PopupMenuButton<String>(
            itemBuilder: (_) => Default.paramLabels.entries.map(
              (element) => PopupMenuItem<String>(
                value: element.key,
                child: Text('Alterar ${element.value}')
              )
            ).toList(),
            icon: const Icon(Icons.settings),
            onSelected: (paramName) => setDefaultParam(context, paramName)
          )
        ]
      ),
      body: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: screenSize.width,
            height: 0.4*screenSize.height,
            child: PageView.builder(
              controller: controller,
              onPageChanged: (value) => setState(() => _currentPage=value),
              // physics: _keepPage ? const NeverScrollableScrollPhysics() : const AlwaysScrollableScrollPhysics(),
              itemBuilder: (context, index) => Padding(
                padding: const EdgeInsets.all(5), 
                child:GestureDetector(
                  onTap: () => setState(_results[index].changeViewState),
                  child: Stack(
                    children: [
                      _results[index].currentImage,
                      Align(
                        alignment: Alignment.topLeft,
                        child: Padding(
                          padding: const EdgeInsets.all(10),
                          child: Text(
                            (index + 1).toString(),
                            style: TextStyle(
                              fontSize: 22,
                              fontWeight: FontWeight.bold,
                              shadows: [
                                for (double i=-1; i <= 1; i++)
                                for (double j=-1; j <= 1; j++)
                                if (i + j != 0)
                                Shadow(color: Colors.white, offset: Offset(i, j))
                              ]
                            )
                          )
                        ) ,
                      )
                    ]
                  ),
                )
              ),
              itemCount: _results.length
            )
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              IconButton(
                onPressed: () => saveImage(path: _results[controller.page!.toInt()].imagePath).then(
                  (message) => showQuickMessage(context, message),
                  onError: (e) => showAlertMessage(context, 'Erro ao tentar salvar imagem!', e.toString())
                ), 
                icon: const Icon(Icons.save)
              ),
              IconButton(
                onPressed: () => Navigator.push(
                  context, 
                  MaterialPageRoute(builder:
                    (context) => ImageView(result: _results[_currentPage])
                  )
                ), 
                icon: const Icon(Icons.zoom_out_map)
              ),
              IconButton(
                onPressed: () => setState(() {
                  _showPostProcess=!_showPostProcess;
                  if (_showPostProcess) _showComments=false;
                }), 
                icon: Icon(Icons.auto_fix_high, color: _showPostProcess ? Colors.red : Colors.black)
              ),
              IconButton(
                onPressed: () => setState(() {
                  _showComments=!_showComments;
                  if (_showComments) _showPostProcess=false;
                }), 
                icon: Icon(Icons.comment, color: _showComments ? Colors.red : Colors.black)
              ),
              if (_results.length > 1)
              IconButton(onPressed: () => showAlertMessage(
                context, 
                'Excluir imagem', 
                'Deseja excluir a imagem ${_currentPage+1}?',
                options: {'Cancelar': false, 'Excluir': true}
              ).then(
                (confirmed) {
                  if (confirmed != null && confirmed){
                    setState(() => _results.removeAt(_currentPage));
                    _currentPage = _results.length-1;
                  }
                }
              ),
              icon: const Icon(Icons.delete_outline))
            ],
          ),
          const Divider(thickness: 2),
          Expanded(
            child: ListView(
              children: [
                Card(
                  child: Column(
                    children: _showPostProcess ? postProcessingTab : (
                      _showComments ? commentsTab : resultsSummaryTab
                    )
                  )
                )
              ],
            )
          )
        ]
      ),
      floatingActionButton: SpeedDial(
        icon: Icons.add,
        children: [
          SpeedDialChild(
            label: 'Câmera',
            onTap: () => pickImageAndResult(ImageSource.camera).then(
              (_) {
                setState(() {});
                controller.animateToPage(_results.length-1, duration: const Duration(seconds: 1), curve: Curves.fastOutSlowIn);
              },
              onError: (e) => showAlertMessage(context, 'Erro ao utilizar a câmera!', e.toString())
            ),
            child: const Icon(Icons.camera_alt_outlined)
          ),
          SpeedDialChild(
            label: 'Galeria',
            onTap: () => pickImageAndResult(ImageSource.gallery).then(
              (_) {
                setState(() {});
                controller.animateToPage(_results.length-1, duration: const Duration(seconds: 1), curve: Curves.fastOutSlowIn);
              },
              onError: (e) => showAlertMessage(context, 'Erro ao escolher imagem!', e.toString())
            ),
            child: const Icon(Icons.image_outlined)
          ),
          SpeedDialChild(
            label: 'Variação da mesma imagem',
            onTap: () => preProcess(_originalPath).then(
              (_) {
                setState(() {});
                controller.animateToPage(_results.length-1, duration: const Duration(seconds: 1), curve: Curves.fastOutSlowIn);
              },
              onError: (e) => showAlertMessage(context, 'Erro ao ajustar imagem!', e.toString())
            ),
            child: const Icon(Icons.crop_rotate_sharp)
          )
        ],
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.endFloat,
    );
  }
}

class ImageView extends StatefulWidget {
  final Result result;

  const ImageView({super.key, required this.result});

  @override
  State<ImageView> createState() => _ImageViewState();
}

class _ImageViewState extends State<ImageView> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.keyboard_backspace),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Row(
          children: [
            const Text('Segmentação'),
            Switch(
              value: widget.result.viewSegState, 
              onChanged: (newValue) => setState(() => widget.result.changeViewState(value: newValue)),
              activeColor: Colors.yellow,
            )
          ],
        )
      ),
      body: PhotoView(
        imageProvider: widget.result.currentProvider,
        minScale: PhotoViewComputedScale.contained,
      )
    );
  }
}