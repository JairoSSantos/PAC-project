import 'dart:io';
import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:gallery_saver/gallery_saver.dart';
import 'package:photo_view/photo_view.dart';
import 'package:http/http.dart' as http;
import 'package:pac_app/config.dart';
import 'package:path_provider/path_provider.dart';

const url = 'https://a72b-2804-1b2-ab42-379f-d82b-2e4b-c160-bd97.ngrok-free.app';

class InfoPage extends StatefulWidget {
  final String imagePath;

  const InfoPage({super.key, required this.imagePath});

  @override
  State<InfoPage> createState() => _InfoPageState();
}

class _InfoPageState extends State<InfoPage> {

  late Map _infoMessages;
  late Map _additionalInfo;
  late MemoryImage _segmentation;
  late ImageProvider _image;
  late bool _segRecived;
  late bool _viewSeg;
  late List _postProcess;

  Future<void> sendImage() async {
    final file = await http.MultipartFile.fromPath('image', widget.imagePath);
    final request = http.MultipartRequest('POST', Uri.parse(url));
    request.files.add(file);
    request.fields.addAll({
      'post_process': json.encode({for (final PyFunction pyfunc in _postProcess) pyfunc.name: pyfunc.asMap()})
    });
    await request.send().then( // Fazer upload da imagem
      (stream) => http.Response.fromStream(stream).then( // obter resposta
        (response) {
          final data = json.decode(response.body.toString());
          final realSize = Default.imageSize * math.sqrt(data['scale']);
          final imageData = const Base64Decoder().convert(data['segmentation'].split(',').last);
          setState((){
            _infoMessages['Área'] = '${data['area'].toStringAsPrecision(4)} mm\u00B2';
            _infoMessages['Dimensões'] = '${realSize.width.round()} mm \u00D7 ${realSize.width.round()} mm';
            _segmentation = MemoryImage(imageData);
            _segRecived = true;
            _viewSeg = true;
          });
        }
      )
    );
  }

  void saveImage(BuildContext context){
    GallerySaver.saveImage(
      widget.imagePath, 
      albumName: 'PAC'
    ).then(
      (bool? saved) {
        if (saved ?? false){
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Imagem salva!'))
          );
        }
      },
      onError: (error) => showDialog(
        context: context, 
        builder: (context) => AlertDialog(
          title: const Text('Erro ao salvar imagem!'),
          content: Text(error.toString())
        )
      )
    );
  }

  Future<void> saveResult(BuildContext context) async {
    final temp = await getTemporaryDirectory();
    final path = '${temp.path}/sample.jpeg';
    final filepath = File(path);
    await filepath.writeAsBytes(_segmentation.bytes);

    final file = await http.MultipartFile.fromPath('image', path);
    final request = http.MultipartRequest('POST', Uri.parse('$url/result'));
    request.files.add(file);

    var info = {};
    info.addAll(_infoMessages);
    info.addAll(_additionalInfo);
    request.fields.addAll({
      'informations': json.encode(info)
    });

    await request.send().then( // Fazer upload da imagem
      (stream) => http.Response.fromStream(stream).then( // obter resposta
        (response) async {
          final data = json.decode(response.body.toString());
          final imageData = const Base64Decoder().convert(data['result'].split(',').last);
          await File(path).writeAsBytes(imageData);
          GallerySaver.saveImage(
            path,
            albumName: 'PAC'
          ).then(
            (bool? saved) {
              if (saved ?? false){
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Imagem salva!'))
                );
              }
            },
            onError: (error) => showDialog(
              context: context, 
              builder: (context) => AlertDialog(
                title: const Text('Erro ao salvar imagem!'),
                content: Text(error.toString())
              )
            )
          );
        }
      )
    );
  }

  Widget getInfoWidget(String title, String subtitle, {Widget? trailing}){
    return Card(
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
  }

  @override
  void initState(){
    super.initState();
    _infoMessages = <String, String>{};
    _additionalInfo = <String, String>{};
    _image = FileImage(File(widget.imagePath));
    _segRecived = false;
    _viewSeg = false;
    sendImage();
    _postProcess = <PyFunction>[];
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Resultado'),
        leading: IconButton(
          icon: const Icon(Icons.keyboard_backspace),
          onPressed: () => Navigator.of(context).popUntil(ModalRoute.withName('/')),
        ),
        actions: [
          PopupMenuButton<String>(
            onSelected: (value){
              switch (value){
                case 'image': 
                  saveImage(context); 
                  break;
                
                case 'result': 
                  saveResult(context);
                  break;
              }
            },
            itemBuilder: (context) => [
              const PopupMenuItem<String>(
                value: 'image',
                child: Text('Salvar imagem')
              ),
              const PopupMenuItem<String>(
                value: 'result',
                child: Text('Salvar resultado')
              )
            ],
            icon: const Icon(Icons.save)
          ),
          PopupMenuButton<String>(
            itemBuilder: (context) => [
              for (final pyfunc in Morphology.values)
              PopupMenuItem<String>(
                value: pyfunc.name, 
                child: Text(pyfunc.label)
              ),
              const PopupMenuItem<String>(
                value: 'add_info',
                child: Text('Adicionar informação')
              )
            ],
            icon: const Icon(Icons.construction),
            onSelected: (value){
              if (value == 'add_info'){
                var title = '';
                var subtitle = '';
                showDialog(
                  context: context, 
                  builder: (_) => AlertDialog(
                    title: TextField(
                      decoration: const InputDecoration(
                        border: UnderlineInputBorder(),
                        labelText: 'Título',
                      ),
                      onChanged: (value){title = value;},
                    ),
                    content: TextField(
                      decoration: const InputDecoration(
                        border: UnderlineInputBorder(),
                        labelText: 'Valor',
                      ),
                      onChanged: (value){subtitle = value;},
                    ),
                    actions: [
                      TextButton(
                        onPressed: () {
                          setState((){_additionalInfo[title] = subtitle;});
                          Navigator.pop(context);
                        }, 
                        child: const Text('Adicionar')
                      ),
                      TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text('Cancelar')
                      )
                    ]
                  )
                );
              } else {
                setState(
                  () => _postProcess.add(Morphology.values.firstWhere(
                    (element) => element.name == value).pyFunc()
                  )
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
                  getInfoWidget(element.key, element.value),
                  for (final MapEntry element in _additionalInfo.entries)
                  getInfoWidget(element.key, element.value,
                    trailing: IconButton(
                      onPressed: () => setState(() => _additionalInfo.remove(element.key)), 
                      icon: const Icon(Icons.delete)
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
                                onChangeEnd: (v) => sendImage(),
                              )
                            ]
                          )
                        ]
                      ),
                      trailing: IconButton(
                        onPressed: () => setState((){
                          _postProcess.remove(pyfunc);
                          sendImage();
                        }), 
                        icon: const Icon(Icons.delete)
                      )
                    )
                  ),
                ],
              )
            )
          )
        ]
      ),
      /*floatingActionButton: SpeedDial(
        icon: Icons.save,
        backgroundColor: Colors.deepOrange,
        children: <SpeedDialChild>[
          SpeedDialChild(
            label: 'Salvar imagem',
            onTap: () => saveImage(context),
            child: const Icon(Icons.add_photo_alternate_outlined)
          ),
          SpeedDialChild(
            label: 'Salvar resultado como imagem',
            child: const Icon(Icons.photo_library_outlined)
          ),
          SpeedDialChild(
            label: 'Salvar resultado como pdf',
            child: const Icon(Icons.picture_as_pdf_outlined)
          )
        ]
      ),*/
    );
  }
}