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

const url = 'http://192.168.15.146:5000';
const pow2Unicode = '\u00B2';

Future<Map> sendImage(String path, {String? route, Map<String, String>? fields}) async {
  final file = await http.MultipartFile.fromPath('image', path);
  final request = http.MultipartRequest('POST', Uri.parse('$url/${(route ?? '')}'));
  request.files.add(file);
  request.fields.addAll(fields ?? {});
  final response = await http.Response.fromStream(await request.send());
  return json.decode(response.body.toString());
}

num sum(Iterable<num> sample) => sample.reduce((a, b) => a + b);

Map<String, num> statistics(Iterable<num> sample){
  final mean = sum(sample)/sample.length;
  final std = math.sqrt(sum(sample.map((x) => math.pow(x - mean, 2)))/sample.length);
  return {
    'Média': mean,
    'Desvio padrão': std,
    'Desvio relativo (%)': (100*std/mean)
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
  String unit = Default.unit;
  bool viewSegState = true;

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

  void changeViewState() => viewSegState=!viewSegState;

  List<String> get summarize => [
    area.toStringAsFixed(Default.precision),
    // scale.toStringAsExponential(Default.precision),
    realSize
  ];

  String get realSize => '${dims.width.round()} \u00D7 ${dims.height.round()}';

  dynamic get currentProvider => (viewSegState && segProvider != null) ? segProvider : imgProvider;

  dynamic get currentImage => (viewSegState && seg != null) ? seg : img;
}

class Root extends StatefulWidget {
  final String originalPath;
  final String initialPath;

  const Root({super.key, required this.originalPath, required this.initialPath});

  @override
  State<Root> createState() => _RootState();
}

class _RootState extends State<Root> {

  late List<Result> _results;
  late bool _isLoading;
  late List<String> _headings;
  late int _currentPage;
  late List<PyFunction> _postProcess;

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

  void showErrorMessage(BuildContext context, String title, String message) => showDialog(
    context: context, 
    builder: (_) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context), 
          child: const Text('Ok')
        )
      ]
    )
  );

  void addInfo(BuildContext context, {String title='', String content=''}) => showDialog(
    context: context, 
    builder: (_) => AlertDialog(
      title: TextField(
        decoration: const InputDecoration(
          border: UnderlineInputBorder(),
          labelText: 'Título',
        ),
        onChanged: ((value) => title=value),
      ),
      content: TextField(decoration: const InputDecoration(
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
              // setState(() => _additionalInfo[title]=content);
              Navigator.pop(context);
            }, 
            child: const Text('Salvar')
          )
        ],
    )
  );

  void setUnit(BuildContext context, {String unit= Default.unit}) => showDialog(
    context: context, 
    builder: (_) => AlertDialog(
      title: const Text('Alterar unidade'),
      content: TextField(
        decoration: InputDecoration(
          border: const UnderlineInputBorder(),
          hintText: unit
        ),
        onChanged: (value) => unit=value
      ),
      actions: [
        TextButton(
          onPressed: () => setState((){
            for (final result in _results){
              result.unit = unit;
            }
            Navigator.pop(context);
          }), 
          child: const Text('Salvar')
        ),
        TextButton(
          onPressed: () => Navigator.pop(context), 
          child: const Text('Cancelar')
        )
      ],
    )
  );

  void postProcessing(BuildContext context) => showDialog(
    context: context, 
    builder: (_) => Dialog.fullscreen(
      backgroundColor: Colors.grey[50],
      child: StatefulBuilder(
        builder: (context, setState) => Column(
          children: [
            AppBar(
              title: const Text('Pós-processamento'),
              leading: IconButton(
                icon: const Icon(Icons.keyboard_backspace),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ),
            Expanded(
              child: ListView(
                shrinkWrap: true,
                children: [
                  Card(
                    child: ListTile(
                      title: Text('Imagem ${_currentPage+1}', textAlign: TextAlign.center,),
                    )
                  ),
                  for (final PyFunction pyfunc in _postProcess)
                  Card(
                    child: ListTile(
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
                                  _postProcess.remove(pyfunc);
                                }), 
                                icon: const Icon(Icons.close)
                              )
                            ]
                          )
                        ]
                      ),
                      // trailing: IconButton(
                      //   onPressed: () => setState((){
                      //     _postProcess.remove(pyfunc);
                      //   }), 
                      //   icon: const Icon(Icons.close)
                      // )
                    )
                  ),
                  DropdownButton(
                    icon: const Icon(Icons.add),
                    items: [
                      for (final Morphology morphology in Morphology.values)
                      DropdownMenuItem(
                        value: morphology.pyFunc(),
                        child: Text(morphology.label)
                      )
                    ], 
                    onChanged: (pyfunc) => setState(() => _postProcess.add(pyfunc!))
                  )
                ],
              ),
            ),
            ButtonBar(
              alignment: MainAxisAlignment.spaceEvenly,
              children: [
                TextButton(
                  onPressed: () => Navigator.pop(context), 
                  child: const Text('Fechar')
                ),
                TextButton(
                  onPressed: () {
                    // setState(() => _additionalInfo[title]=content);
                    Navigator.pop(context);
                  }, 
                  child: const Text('Aplicar')
                )
              ],
            )
          ],
        ),
      ) 
    )
  );

  Future<void> preProcess(String path) async {
    CroppedFile? croppedImage = await ImageCropper().cropImage(
      sourcePath: path,
      aspectRatio: const CropAspectRatio(ratioX: 1, ratioY: 1)
    );
    if (croppedImage != null) {
      final newResult = Result(imagePath: croppedImage.path);
      await newResult.determinate().whenComplete(() => _results.add(newResult));
    }
  }

  Future<void> pickImageAndResult(ImageSource source) async {
    XFile? imageXFile = await ImagePicker().pickImage(source: source);
    if (imageXFile != null){
      preProcess(imageXFile.path);
    }
  }

  @override
  void initState() {
    super.initState();

    _results = [];
    final initialResult = Result(imagePath: widget.initialPath);
    initialResult.determinate().whenComplete(
      () => setState(() => _results.add(initialResult))
    );
    _isLoading = false;
    _currentPage = 0;

    _headings = [
      'Id',
      'Área (${Default.unit}$pow2Unicode)', 
      // 'Escala (px/${Default.unit}\u00B2)', 
      'Tamanho (${Default.unit})'
    ];

    _postProcess = [];
  }

  @override
  Widget build(BuildContext context) {
    final PageController controller = PageController(viewportFraction: 0.85);
    final screenSize = MediaQuery.of(context).size;

    return Scaffold(
      backgroundColor: Colors.grey[250],
      appBar: AppBar(
        // title: const Text(''),
        leading: IconButton(
          icon: const Icon(Icons.keyboard_backspace),
          onPressed: () => Navigator.of(context).popUntil(ModalRoute.withName('/')),
        ),
        actions: [
          if (_isLoading) Transform.scale(
            scaleX: 0.6,
            scaleY: 0.4,
            child: const CircularProgressIndicator(color: Colors.white)
          ),
          IconButton(
            onPressed: () {}, 
            icon: const Icon(Icons.upload_file)
          ),
          PopupMenuButton<String>(
            itemBuilder: (_) => [
              for (final pyfunc in Morphology.values)
              PopupMenuItem<String>(
                value: pyfunc.name, 
                child: Text(pyfunc.label)
              ),
              const PopupMenuItem<String>(
                value: 'add_info',
                child: Text('Adicionar comentário')
              ),
              const PopupMenuItem<String>(
                value: 'set_unit',
                child: Text('Alterar unidade')
              )
            ],
            // icon: const Icon(Icons.more_vert),
            // onSelected: (value) {
            //   if (value == 'add_info'){
            //     addInfo(context);
            //   } else if (value == 'set_unit') {
            //     setUnit(context);
            //   }
              // } else {
              //   setState(() => _postProcess.add(Morphology.values.firstWhere(
              //     (element) => element.name == value).pyFunc()
              //   ));
              //   getResults().catchError(
              //     (error) => showErrorMessage(context, 'Erro!', error.toString())
              //   );
              // }
            // }
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
                  onError: (e) => showErrorMessage(context, 'Erro ao tentar salvar imagem!', e.toString())
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
                onPressed: () => postProcessing(context), 
                icon: const Icon(Icons.auto_fix_high)
              ),
              IconButton(onPressed: (){}, icon: const Icon(Icons.grid_on)),
              if (_results.length > 1)
              IconButton(onPressed: (){}, icon: const Icon(Icons.delete_outline))
            ],
          ),
          const Divider(thickness: 2),
          Expanded(child: ListView(
            children: [
              Card(
                child: Column(
                  children: [
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
                            children: [(index+1).toString(), ..._results[index].summarize].map(
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
                            children: const [
                              TableCell(child: Text('')),
                              TableCell(
                                child: Text(
                                  'Área (${Default.unit}\u00B2)',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
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
                                  element.value.toStringAsFixed(Default.precision), 
                                  textAlign: TextAlign.center
                                )
                              )
                            ]
                          ),
                        ]
                      )
                    )
                  ]
                )
              )
            ],
          ))
        ]
      ),
      floatingActionButton: SpeedDial(
        icon: Icons.add,
        children: [
          SpeedDialChild(
            label: 'Câmera',
            onTap: () => pickImageAndResult(ImageSource.camera).then(
              (value) {
                setState(() {});
                controller.animateToPage(_results.length-1, duration: const Duration(seconds: 1), curve: Curves.fastOutSlowIn);
              },
              onError: (e) => showErrorMessage(context, 'Erro ao utilizar a câmera!', e.toString())
            ),
            child: const Icon(Icons.camera_alt_outlined)
          ),
          SpeedDialChild(
            label: 'Galeria',
            onTap: () => pickImageAndResult(ImageSource.gallery).then(
              (value) {
                setState(() {});
                controller.animateToPage(_results.length-1, duration: const Duration(seconds: 1), curve: Curves.fastOutSlowIn);
              },
              onError: (e) => showErrorMessage(context, 'Erro ao escolher imagem!', e.toString())
            ),
            child: const Icon(Icons.image_outlined)
          ),
          SpeedDialChild(
            label: 'Variação da mesma imagem',
            onTap: () => preProcess(widget.originalPath).then(
              (value) {
                setState(() {});
                controller.animateToPage(_results.length-1, duration: const Duration(seconds: 1), curve: Curves.fastOutSlowIn);
              },
              onError: (e) => showErrorMessage(context, 'Erro ao ajustar imagem!', e.toString())
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
      ),
      body: GestureDetector(
        onTap: () => setState(widget.result.changeViewState),
        child: PhotoView(
          imageProvider: widget.result.currentProvider,
          minScale: PhotoViewComputedScale.contained,
        ),
      )
    );
  }
}