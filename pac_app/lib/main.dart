// import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:flutter/services.dart';
import 'package:image_cropper/image_cropper.dart';
import 'package:pac_app/info_page.dart';
import 'package:flutter_speed_dial/flutter_speed_dial.dart';

void main() async {
  runApp(const MaterialApp(home: App()));
}

class App extends StatefulWidget {

  const App({super.key});

  @override
  State<App> createState() => _AppState();
}

class _AppState extends State<App> {

  final _introductionText = {
    'Como tirar uma boa foto?': [
      ['1º', 'Com a amostra sobre o papel milímetrado, posicione a câmera paralelamente à superfície e tire a foto (lembre-se de manter o ambiente bem iluminado).'], 
      ['2º', 'Rotacione a imagem para deixá-la alinhada com as linhas do papel milimetrado.'], 
      ['3º', 'Recorte a imagem mantendo a maior parte (60-80%) de papel milímetrado.'],
      ['', 'Observação: Para facilitar a avaliação dos resultados, recorte a imagem posicionando os seus cantos sobre vértices do papel milímetrado.']
    ],
    'Como avaliar os resultados?': [
      ['\u2713', 'Primeiramente, verifique se a escala de conversão foi encontrada com sucesso, observando as dimensões fornecidas e comparando com o observado na imagem.'],
      ['\u2713', 'Quanto à segmentação, é possível dar zoom na imagem e verificar o grau do erro no resultado.'],
      ['\u2713', 'Caso seja observado que houve uma boa segmentação, porém com pequenos buracos ou excessos, você pode aplicar a função "Remover buracos" ou "Remover excessos", respectivamente.'],
    ]
  };

  void showErrorMessage(BuildContext context, String title, String message){
    showDialog(
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
  }

  Future<String?> pickImage(ImageSource source) async {
    XFile? imageXFile = await ImagePicker().pickImage(source: source);
    String? imagePath;
    if (imageXFile != null){
      CroppedFile? croppedImage = await ImageCropper().cropImage(
        sourcePath: imageXFile.path,
        aspectRatio: const CropAspectRatio(ratioX: 1, ratioY: 1)
      );
      imagePath = croppedImage?.path;
    }
    return imagePath;
  }

  Future<void> pushInfoPage(BuildContext context, String? imagePath) async {
    /*
    Este procedimento será chamado após cropImage,
    sendo necessário, portanto, verificar se o usuário 
    aceitou proseguir para InfoPage `assert (imagePath is String)`
    ou se o usuário decidiu retornar à câmera `assert (imagePath == null)`.
    */
    if (imagePath != null){
      await Navigator.push(
        context,
        MaterialPageRoute(builder: (context) => Root(imagePath: imagePath))
      );
    }
  }

  @override
  void initState() {
    super.initState();
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp
    ]);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(title: const Text('Pellet Area Calculator')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: ListView(
            children: [
              for (final element in _introductionText.entries)
              Card(
                child: Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.only(top: 2, bottom: 2),
                      child: Text(element.key, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold))
                    ),
                    for (final List<String> value in element.value)
                    ListTile(
                      leading: Text(value[0], style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                      title: Text(value[1]),
                      minLeadingWidth : 0,
                      minVerticalPadding: 10,
                    ),
                  ],
                )
              ),
            ],
          ),
        )
      ),
      floatingActionButton: SpeedDial(
        icon: Icons.add,
        children: [
          SpeedDialChild(
            onTap: () => pickImage(ImageSource.camera).then(
              (path) => pushInfoPage(context, path),
              onError: (error) => showErrorMessage(context, 'Erro ao utilizar a câmera!', error.toString())
            ),
            child: const Icon(Icons.camera_alt_outlined)
          ),
          SpeedDialChild(
            onTap: () => pickImage(ImageSource.gallery).then(
              (path) => pushInfoPage(context, path),
              onError: (error) => showErrorMessage(context, 'Erro ao escolher imagem!', error.toString())
            ),
            child: const Icon(Icons.image_outlined)
          )
        ],
      ),
      bottomNavigationBar: BottomAppBar(
        shape: const CircularNotchedRectangle(),
        child: Container(height: 50.0),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.miniEndDocked,
    );
  }
}