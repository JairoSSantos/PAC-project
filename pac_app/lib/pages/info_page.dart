import 'dart:io';
import 'package:pac_app/config.dart';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:flutter_speed_dial/flutter_speed_dial.dart';
import 'package:gallery_saver/gallery_saver.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

// ignore: must_be_immutable
class InfoPage extends StatefulWidget {
  late String imagePath;

  InfoPage({super.key, required this.imagePath});

  @override
  State<InfoPage> createState() => _InfoPageState();
}

class _InfoPageState extends State<InfoPage> {

  final _infoMessages = [
    'Área: 0.00',
    'Escala: 0.00',
    'Erro estimado: 0.00'
  ];

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
      ),
      body: Column(
        children: <Widget>[
          Image.file(File(widget.imagePath),
            width: size.width,
            height: size.width,
            fit: BoxFit.fill
          ),
          Expanded(
            //height: 300,
            child: ListView.builder(
                itemBuilder: (context, index) => Card(
                  child: ListTile(title: Text(_infoMessages[index]))
                ), 
                itemCount: _infoMessages.length
            )
          )
        ]
      ),
      floatingActionButton: SpeedDial(
        icon: Icons.save,
        children: <SpeedDialChild>[
          SpeedDialChild(
            label: 'Salvar imagem',
            onTap: () => GallerySaver.saveImage(
                widget.imagePath, 
                albumName: 'PAC'
              ).then(
              (path) {
                const snackBar = SnackBar(content: Text('Imagem salva!'));
                ScaffoldMessenger.of(context).showSnackBar(snackBar);
              }
            ),
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

class Cropper extends StatefulWidget {
  final XFile imageXFile;

  const Cropper({super.key, required this.imageXFile});

  @override
  State<Cropper> createState() => _CropperState();
}

class _CropperState extends State<Cropper> {

  late double _left;
  late double _top;

  var _isLoading = false;

  @override
  Widget build(BuildContext context) {

    final size = MediaQuery.of(context).size;
    final imageSize = getImageSize(widget.imageXFile.path);
    final alpha = size.width/imageSize.width;
    final pelletField = PelletField(
      size: Size(
        getImageWidth()*alpha,
        getImageHeight()*alpha,
      )
    );

    _left = (size.width - pelletField.size.width)/2;
    _top = (size.height - pelletField.size.height)/2;

    final imageWidget = Image.file(File(widget.imageXFile.path));

    return Scaffold(
      body: _isLoading ? const Center(child: CircularProgressIndicator()) :
      Stack(
        children: [
          Center(child: imageWidget),
          StatefulBuilder(
            builder: (context, setNewState) => Positioned(
              left: _left,
              top: _top,
              child: GestureDetector(
                onPanUpdate: (details) => setNewState(() {
                    //debugPrint('$_left, $_top');
                    _left += details.delta.dx;
                    _top += details.delta.dy;
                }),
                child: pelletField,
              ),
            )
          ),
        ]
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          //setState(() {_isLoading = true;});
          final tempDir = await getTemporaryDirectory();
          final imagePath = p.join(tempDir.path, widget.imageXFile.name);
          regularizeImage(widget.imageXFile.path, 
            left: _left/alpha,
            top: (_top - (size.height - size.width*imageSize.height/imageSize.width)/2)/alpha,
            finalPath: imagePath
          ).then((_) {
              //Navigator.pop(context);
              Navigator.push(
              context, 
              MaterialPageRoute(
                builder: (context) => InfoPage(imagePath: imagePath)
              )
            );
          });
        }, 
        child: const Icon(Icons.crop)
      ),
    );
  }
}