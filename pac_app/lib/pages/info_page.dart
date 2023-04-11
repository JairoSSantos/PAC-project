import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_speed_dial/flutter_speed_dial.dart';
import 'package:gallery_saver/gallery_saver.dart';
import 'package:photo_view/photo_view.dart';
import 'package:http/http.dart' as http;
import 'package:pac_app/config.dart';

const url = 'https://b9d6-2804-1b2-ab41-b2a3-a559-2742-574c-3db6.ngrok-free.app';

class InfoPage extends StatefulWidget {
  final String imagePath;

  const InfoPage({super.key, required this.imagePath});

  @override
  State<InfoPage> createState() => _InfoPageState();
}

class _InfoPageState extends State<InfoPage> {

  late Map _infoMessages;
  late ImageProvider _segmentation;
  late String _imageKey;

  Future<void> getScale() async {
    final response = await http.get(Uri.parse('$url/scale/$_imageKey'));
    final data = json.decode(response.body.toString());
    final realSize = getImageSize(widget.imagePath) * math.sqrt(data['scale']);
    setState(() {
      _infoMessages['Dimensões da imagem'] = '${realSize.width.round()} mm \u2A09 ${realSize.width.round()} mm';
    });
  }

  Future<void> getArea() async {
    final response = await http.get(Uri.parse('$url/area/$_imageKey'));
    final data = json.decode(response.body.toString());
    setState(() {
      _infoMessages['Área'] = '${data['area'].toStringAsPrecision(4)} mm\u00B2';
    });
  }

  Future<void> getSegmentation() async {
    final response = await http.get(Uri.parse('$url/segmentation/$_imageKey'));
    final data = json.decode(response.body.toString());
    final imageData = const Base64Decoder().convert(data['segmentation'].split(',').last);
    setState(() {
      _segmentation = MemoryImage(imageData);
    });
  }

  void finishServer() => http.get(Uri.parse('$url/finish/$_imageKey'));

  void getResults() async {
    await getScale();
    await getArea();
    await getSegmentation();
    finishServer();
  }

  Future<void> sendImage() async {
    final file = await http.MultipartFile.fromPath('image', widget.imagePath);
    final request = http.MultipartRequest('POST', Uri.parse(url));
    request.files.add(file);
    await request.send().then( // Fazer upload da imagem
      (stream) => http.Response.fromStream(stream).then( // obter resposta
        (response){
          _imageKey = json.decode(response.body.toString())['key'];
        }
      )
    );
    getResults();
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
    _segmentation = FileImage(File(widget.imagePath));
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
              imageProvider: _segmentation,
              minScale: PhotoViewComputedScale.covered,
              customSize: Size(size.width, size.width)
            )
          ),
          Expanded(
            child: Container(
              decoration: const BoxDecoration(color: Colors.white),
              child: ListView.builder(
                itemBuilder: (context, index) => Card(
                  child: ListTile(title: RichText(
                    text: TextSpan(
                      style: DefaultTextStyle.of(context).style,
                      children: [
                        TextSpan(text: '${_infoMessages.keys.elementAt(index)}: '),
                        TextSpan(
                          text: _infoMessages.values.elementAt(index), 
                          style: const TextStyle(
                            fontStyle: FontStyle.italic, 
                            fontWeight: FontWeight.bold,
                            fontSize: 18
                          )
                        ),
                      ]
                    )
                  )),
                ), 
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