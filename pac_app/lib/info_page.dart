import 'dart:io';
import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:gallery_saver/gallery_saver.dart';
import 'package:photo_view/photo_view.dart';
import 'package:http/http.dart' as http;
import 'package:pac_app/config.dart';
import 'package:path_provider/path_provider.dart';

const url = 'http://192.168.15.146:5000';

Future<Map> sendImage(String path, {String? route, Map<String, String>? fields}) async {
  final file = await http.MultipartFile.fromPath('image', path);
  final request = http.MultipartRequest('POST', Uri.parse('$url/${(route ?? '')}'));
  request.files.add(file);
  request.fields.addAll(fields ?? {});
  final response = await http.Response.fromStream(await request.send());
  return json.decode(response.body.toString());
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
    img = Image.file(imgFile);
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
    dims = Default.imageSize * math.sqrt(scale);
    final segData = const Base64Decoder().convert(response['segmentation'].split(',').last);
    seg = Image.memory(segData);
    segProvider = MemoryImage(segData);
    viewSegState = true;
  }

  void changeViewState() => viewSegState=!viewSegState;

  List<String> get summarize => [
    area.toStringAsPrecision(4).toString(),
    scale.toStringAsExponential(2),
    '${dims.width.round()} \u00D7 ${dims.height.round()}'
  ];

  // ignore: non_constant_identifier_names
  // String get Area => finished ? '${area.toStringAsPrecision(4)} $unit\u00B2' : '';
  
  // // ignore: non_constant_identifier_names
  // String get Scale => finished ? '${scale.toStringAsExponential()} $unit\u207B\u00B2' : '';

  // // ignore: non_constant_identifier_names
  // String get Dims => finished ? '${dims.width.round()} $unit \u00D7 ${dims.height.round()} $unit' : '';

  dynamic get currentProvider => (viewSegState && segProvider != null) ? segProvider : imgProvider;

  dynamic get currentImage => (viewSegState && seg != null) ? seg : img;
}

class Root extends StatefulWidget {
  final String imagePath;

  const Root({super.key, required this.imagePath});

  @override
  State<Root> createState() => _RootState();
}

class _RootState extends State<Root> {

  late List<Result> _results;
  late Map _saveSettings;
  late bool _isLoading;
  late List _headings;

  void setLoading(value) => setState(() => _isLoading=value);

  void showSaveSettings(BuildContext context) => showDialog(
    context: context, 
    builder: (context) => StatefulBuilder(
      builder: (context, setState) => AlertDialog(
        title: const Text('Salvar'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (MapEntry element in _saveSettings.entries)
            CheckboxListTile(
              title: Text(element.key),
              value: element.value, 
              onChanged: (newValue) => setState(() {
                _saveSettings[element.key] = newValue;
              })
            )
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context), 
            child: const Text('Cancelar')
          ),
          TextButton(
            onPressed: (){
              // save();
              Navigator.pop(context);
            }, 
            child: const Text('Salvar')
          ),
        ]
      )
    )
  );

  // Future<String> saveImage({String? path}) async {
  //   setLoading(true);
  //   final success = await GallerySaver.saveImage(
  //     path ?? widget.imagePath, 
  //     albumName: 'PAC'
  //   );
  //   setLoading(false);
  //   return (success ?? false) ? 'Imagem salva!' : 'Erro ao salvar imagem!';
  // }

  // Future<void> save() async {
  //   setLoading(true);
  //   String path = widget.imagePath;
  //   if (_saveSettings['Segmentação']) {
  //     path = '${(await getTemporaryDirectory()).path}/sample.jpeg';
  //     await File(path).writeAsBytes(_segmentation.bytes);
  //   }

  //   Map info = {};
  //   if (_saveSettings['Área']) info.addAll({'Área':_infoMessages['Área']});
  //   if (_saveSettings['Dimensões']) info.addAll({'Dimensões':_infoMessages['Dimensões']});
  //   if (_saveSettings['Comentários']) info.addAll(_additionalInfo);
  //   final response = await sendImage(path, 
  //     route: 'result',
  //     fields: {'informations': json.encode(info)}
  //   );
  //   final imageData = const Base64Decoder().convert(response['result'].split(',').last);
  //   await File(path).writeAsBytes(imageData);
  //   setLoading(false);
  //   saveImage(path: path).then((message) => showQuickMessage(context, message));
  // }

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

  @override
  void initState() {
    super.initState();

    _results = List.filled(3, Result(imagePath: widget.imagePath));

    _saveSettings = {
      'Segmentação': true,
      'Área': true,
      'Dimensões': true,
      'Comentários': true
    };

    _headings = [
      'Id',
      'Área (${Default.unit}\u00B2)', 
      'Escala (${Default.unit}\u207B\u00B2)', 
      'Tamanho (${Default.unit})'
    ];

    setLoading(false);
    for (final result in _results) {
      result.determinate().whenComplete(() => setState((){}));
    }
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
            onPressed: () => showSaveSettings(context), 
            icon: const Icon(Icons.save)
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
            height: 0.425*screenSize.height,
            child: PageView.builder(
              controller: controller,
              itemBuilder: (context, index) => Padding(
                padding: const EdgeInsets.all(5), 
                child: GestureDetector(
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
          Card(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                IconButton(onPressed: (){}, icon: const Icon(Icons.save)),
                IconButton(onPressed: (){}, icon: const Icon(Icons.zoom_out_map)),
                IconButton(onPressed: (){}, icon: const Icon(Icons.auto_fix_high)),
              ],
            )
          ),
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
                      0: FractionColumnWidth(0.1)
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
                        children: [(index+1).toString(), ..._results[index].summarize].map(
                          (value) => TableCell(child: Text(value, textAlign: TextAlign.center))
                        ).toList()
                      )
                    ]
                  )
                )
              ]
            )
          )
        ]
      )
    );
  }
}