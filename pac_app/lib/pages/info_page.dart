import 'dart:io';
import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_speed_dial/flutter_speed_dial.dart';
import 'package:gallery_saver/gallery_saver.dart';
import 'package:photo_view/photo_view.dart';
import 'package:http/http.dart' as http;
import 'package:pac_app/config.dart';

const url = 'https://8213-2804-1b2-ab41-fd88-b0ed-5cf1-faf6-8aaf.ngrok-free.app';

class InfoPage extends StatefulWidget {
  final String imagePath;

  const InfoPage({super.key, required this.imagePath});

  @override
  State<InfoPage> createState() => _InfoPageState();
}

class _InfoPageState extends State<InfoPage> {

  late Map _infoMessages;
  late ImageProvider _segmentation;
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
            _infoMessages['Dimensões da imagem'] = '${realSize.width.round()} mm \u2A09 ${realSize.width.round()} mm';
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

  @override
  void initState(){
    super.initState();
    _infoMessages = <String, String>{};
    _segmentation = _image = FileImage(File(widget.imagePath));
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
            onSelected: (name) => setState(
              () => _postProcess
                .add(Morphology.values.firstWhere((element) => element.name == name).pyFunc())
            ),
            itemBuilder: (context) => [
              for (final pyfunc in Morphology.values)
              PopupMenuItem<String>(
                value: pyfunc.name, 
                child: Text(pyfunc.label))
            ],
            icon: const Icon(Icons.construction)
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
                  Card(
                    child: ListTile(
                      title: Padding(
                        padding: const EdgeInsets.only(bottom: 10.0, top: 10.0),
                        child: Text('${element.key}: '),
                      ),
                      subtitle: Center(child: Text(element.value, style: const TextStyle(fontSize: 20, fontWeight:FontWeight.bold))),
                      //minVerticalPadding: 50,
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
                      )
                    )
                  ),
                ],
              )
            )
          )
        ]
      ),
      floatingActionButton: SpeedDial(
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
      ),
    );
  }
}