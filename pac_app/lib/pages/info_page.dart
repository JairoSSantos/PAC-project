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

const url = 'https://dd29-2804-1b2-ab40-f65f-38fe-2377-ea1c-70d8.sa.ngrok.io';

class ImageInfo{
  final String path;
  var _sigma = 0.0;
  var _size = Size.zero;
  var _area = 0.0;
  late ImageProvider _segmentation;

  ImageInfo({required this.path}){
    _segmentation = FileImage(File(path));
  }

  double get sigma => _sigma;
  Size get size => _size;
  double get area => _area;
  ImageProvider get segmentation => _segmentation;

  void updateInfo(Map<String, dynamic> info){
    _sigma = double.parse(info['scale']);
    _size = getImageSize(path) * math.sqrt(_sigma);
    _segmentation = MemoryImage(convertBase64Image(info['segmentation']));
    _area = double.parse(info['area']);
  }

  Uint8List convertBase64Image(String base64String) {
    return const Base64Decoder().convert(base64String.split(',').last);
  }

  Future<void> request() async {
    final file = await http.MultipartFile.fromPath('image', path);
    final request = http.MultipartRequest('POST', Uri.parse(url))
      ..files.add(file);
    await request.send().then( // Fazer upload da image
      (response) => http.Response.fromStream(response).then( // obter resposta
        (response) => updateInfo( // atualizar informações sobre a imagem
          json.decode(response.body.toString()) // converter resposta do servidor para um objeto Map
        )
      )
    );
    //request.finalize();
  }
}

class InfoPage extends StatefulWidget {
  late final ImageInfo imageInfo;

  InfoPage({super.key, required imagePath}){
    imageInfo = ImageInfo(path: imagePath);
  }

  @override
  State<InfoPage> createState() => _InfoPageState();
}

class _InfoPageState extends State<InfoPage> {

  var _infoMessages = {
    'Área': '',
    'Dimensões da imagem': '',
  };

  void saveImage(BuildContext context){
    GallerySaver.saveImage(
      widget.imageInfo.path, 
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
    widget.imageInfo.request().whenComplete(
      () => setState(
        (){
          _infoMessages['Área'] = '${widget.imageInfo.area.toStringAsPrecision(4)} mm\u00B2';
          _infoMessages['Dimensões da imagem'] = '${widget.imageInfo.size.width.round()} mm \u2A09 ${widget.imageInfo.size.width.round()} mm';
        }
      )
    );
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
              imageProvider: widget.imageInfo.segmentation,
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
                itemCount: _infoMessages.length
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