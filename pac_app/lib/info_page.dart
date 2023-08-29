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

class InfoPage extends StatefulWidget {
  final String imagePath;

  const InfoPage({super.key, required this.imagePath});

  @override
  State<InfoPage> createState() => _InfoPageState();
}

class _InfoPageState extends State<InfoPage> {

  late Map _infoMessages; // resultados do modelo
  late Map _additionalInfo; // informações adicionadas pelo usuário
  late Map _saveSettings;
  late List _postProcess; // processamentos adicionais
  late MemoryImage _segmentation; // segmentação
  late ImageProvider _image; // amostra
  late bool _segRecived; // true se a segmentação estiver disponível
  late bool _viewSeg; // true para solicitar que a amostra seja mostrada
  late bool _isLoading; // true para indicar algum processo em andamento
  late String _unit;

  void setLoading(value) => setState(() => _isLoading=value);

  Future<void> getResults() async {
    setLoading(true);
    final response = await sendImage(widget.imagePath, 
      fields:{
        'post_process': json.encode({
          for (final PyFunction pyfunc in _postProcess) 
          pyfunc.name: pyfunc.asMap()
        })
      }
    );
    final realSize = Default.imageSize * math.sqrt(response['scale']);
    final segData = const Base64Decoder().convert(response['segmentation'].split(',').last);
    setState((){
      _infoMessages['Área'] = '${response['area'].toStringAsPrecision(4)} $_unit\u00B2';
      _infoMessages['Dimensões'] = '${realSize.width.round()} $_unit \u00D7 ${realSize.width.round()} $_unit';
      _segmentation = MemoryImage(segData);
      _segRecived = true;
      _viewSeg = true;
    });
    setLoading(false);
  }

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
              save();
              Navigator.pop(context);
            }, 
            child: const Text('Salvar')
          ),
        ]
      )
    )
  );

  Future<String> saveImage({String? path}) async {
    setLoading(true);
    final success = await GallerySaver.saveImage(
      path ?? widget.imagePath, 
      albumName: 'PAC'
    );
    setLoading(false);
    return (success ?? false) ? 'Imagem salva!' : 'Erro ao salvar imagem!';
  }

  Future<void> save() async {
    setLoading(true);
    String path = widget.imagePath;
    if (_saveSettings['Segmentação']) {
      path = '${(await getTemporaryDirectory()).path}/sample.jpeg';
      await File(path).writeAsBytes(_segmentation.bytes);
    }

    Map info = {};
    if (_saveSettings['Área']) info.addAll({'Área':_infoMessages['Área']});
    if (_saveSettings['Dimensões']) info.addAll({'Dimensões':_infoMessages['Dimensões']});
    if (_saveSettings['Comentários']) info.addAll(_additionalInfo);
    final response = await sendImage(path, 
      route: 'result',
      fields: {'informations': json.encode(info)}
    );
    final imageData = const Base64Decoder().convert(response['result'].split(',').last);
    await File(path).writeAsBytes(imageData);
    setLoading(false);
    saveImage(path: path).then((message) => showQuickMessage(context, message));
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
              setState(() => _additionalInfo[title]=content);
              Navigator.pop(context);
            }, 
            child: const Text('Salvar')
          )
        ],
    )
  );
    
    void setUnit(BuildContext context, String unit) => showDialog(
    context: context, 
    builder: (_) => AlertDialog(
      title: const Text('Alterar unidade'),
      content: TextField(
        decoration: InputDecoration(
          border: const UnderlineInputBorder(),
          hintText: unit
        ),
        onChanged: (value) {unit = value;}
      ),
      actions: [
        TextButton(
          onPressed: () => setState((){
            _unit = unit;
            getResults().catchError(
              (error) => showErrorMessage(context, 'Erro!', error.toString())
            );
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

  Widget infoWidget(String title, String subtitle, {Widget? trailing}) => Card(
    child: ListTile(
      title: Padding(
        padding: const EdgeInsets.only(bottom: 10.0, top: 10.0),
        child: Text(title),
      ),
      subtitle: Center(
        child: Text(
          subtitle, 
          style: const TextStyle(fontSize: 20, fontWeight:FontWeight.bold)
        )
      ),
      trailing: trailing,
    )
  );

  @override
  void initState(){
    super.initState();

    _infoMessages = <String, String>{};
    _additionalInfo = <String, String>{};
    _saveSettings = {
      'Segmentação': true,
      'Área': true,
      'Dimensões': true,
      'Comentários': true
    };
    _image = FileImage(File(widget.imagePath));
    _segRecived = false;
    _viewSeg = false;
    _postProcess = <PyFunction>[];
    _isLoading = false;
    _unit = Default.unit;
    getResults();
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      resizeToAvoidBottomInset: false,
      appBar: AppBar(
        title: const Text('Resultado'),
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
          IconButton(onPressed: () => showSaveSettings(context), icon: const Icon(Icons.save)),
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
            icon: const Icon(Icons.more_vert),
            onSelected: (value) {
              if (value == 'add_info'){
                addInfo(context);
              } else if (value == 'set_unit') {
                setUnit(context, _unit);
              } else {
                setState(() => _postProcess.add(Morphology.values.firstWhere(
                  (element) => element.name == value).pyFunc()
                ));
                getResults().catchError(
                  (error) => showErrorMessage(context, 'Erro!', error.toString())
                );
              }
            }
          )
        ]
      ),
      body: Column(
        children: <Widget>[
          SizedBox(
            width: size.width, 
            height: size.width,
            child: PhotoView(
              imageProvider: _viewSeg ? _segmentation : _image,
              minScale: PhotoViewComputedScale.covered,
              customSize: Size(size.width, size.width)
            )
          ),
          Expanded(
            child: Container(
              decoration: const BoxDecoration(color: Colors.white),
              child: ListView(
                children: [
                  for (final MapEntry element in _infoMessages.entries)
                  infoWidget(element.key, element.value),
                  for (final MapEntry element in _additionalInfo.entries)
                  infoWidget(element.key, element.value,
                    trailing: IconButton(
                      onPressed: () => setState(() => _additionalInfo.remove(element.key)), 
                      icon: const Icon(Icons.close)
                    )
                  ),
                  if (_segRecived)
                  Card(
                    child: ListTile(
                      title: Row(children:[
                        const Text('Segmentação'),
                        Switch(value: _viewSeg, onChanged: (v) => setState((){_viewSeg = v;}))
                      ]),
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
                                onChanged: (v) => setState((){param.value = v.round();}),
                                onChangeEnd: (_) => getResults().catchError(
                                  (error) => showErrorMessage(context, 'Erro!', error.toString())
                                ),
                              )
                            ]
                          )
                        ]
                      ),
                      trailing: IconButton(
                        onPressed: () => setState((){
                          _postProcess.remove(pyfunc);
                          getResults().catchError(
                            (error) => showErrorMessage(context, 'Erro!', error.toString())
                          );
                        }), 
                        icon: const Icon(Icons.close)
                      )
                    )
                  ),
                ],
              )
            )
          )
        ]
      ),
    );
  }
}