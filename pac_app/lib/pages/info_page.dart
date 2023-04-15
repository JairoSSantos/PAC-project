import 'dart:io';
import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_speed_dial/flutter_speed_dial.dart';
import 'package:gallery_saver/gallery_saver.dart';
import 'package:photo_view/photo_view.dart';
import 'package:http/http.dart' as http;
import 'package:pac_app/config.dart';

const url = 'https://f729-2804-1b2-ab41-fd88-a559-2742-574c-3db6.ngrok-free.app';

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
  late bool _viewSegmentation;

  Future<void> sendImage() async {
    final file = await http.MultipartFile.fromPath('image', widget.imagePath);
    final request = http.MultipartRequest('POST', Uri.parse(url));
    request.files.add(file);
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
            _infoMessages['Segmentação'] = '__seg__';
            _viewSegmentation = true;
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
    _viewSegmentation = false;
    sendImage();
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
          IconButton(onPressed: (){}, icon: const Icon(Icons.construction))
        ]
      ),
      body: Column(
        children: <Widget>[
          SizedBox(
            width: size.width, 
            height: size.width,
            child: PhotoView(
              imageProvider: _viewSegmentation ? _segmentation : _image,
              minScale: PhotoViewComputedScale.covered,
              customSize: Size(size.width, size.width)
            )
          ),
          Expanded(
            child: Container(
              decoration: const BoxDecoration(color: Colors.white),
              child: ListView.builder(
                itemBuilder: (context, index) {
                  final value = _infoMessages.values.elementAt(index);
                  return Card(
                    child: 
                    (value == '__seg__') ?
                    ListTile(
                      title: Row(children:[
                        Text('${_infoMessages.keys.elementAt(index)}: '), 
                        Switch(value: _viewSegmentation, onChanged: (v) => setState((){_viewSegmentation = v;}))
                      ]),
                    ) :
                    ListTile(
                      title: RichText(
                        text: TextSpan(
                          style: DefaultTextStyle.of(context).style,
                          children: [
                            TextSpan(text: '${_infoMessages.keys.elementAt(index)}: '),
                            TextSpan(
                              text: value, 
                              style: const TextStyle(
                                fontStyle: FontStyle.italic, 
                                fontWeight: FontWeight.bold,
                                fontSize: 18
                              )
                            ),
                          ]
                        )
                      )
                    ),
                  ); 
                },
                itemCount: _infoMessages.length,
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