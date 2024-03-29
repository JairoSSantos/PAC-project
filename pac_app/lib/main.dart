// import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:flutter/services.dart';
import 'package:image_cropper/image_cropper.dart';
import 'package:pac_app/info_page.dart';
import 'package:flutter_speed_dial/flutter_speed_dial.dart';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:open_filex/open_filex.dart';
import 'package:pac_app/config.dart';
import 'package:http/http.dart' as http;

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
      ['', 'Observação: Para facilitar a avaliação dos resultados, recorte a imagem posicionando os seus cantos sobre vértices do papel milímetrado.'],
      ['4º', 'Repita os passos anteriores para a mesma amostra, aumentando seu conjunto de imagens.'],
      ['5º', 'Adicione um nome à amostra e salve um relatório com os resultados encontrados.'],
    ],
    'Como avaliar os resultados?': [
      ['\u2713', 'Primeiramente, verifique se a escala de conversão foi encontrada com sucesso, observando a largura fornecida e comparando com o observado na respectiva imagem.'],
      ['\u2713', 'Quanto à segmentação, é possível dar zoom nas imagens e verificar o grau do erro no resultado.'],
      ['\u2713', 'Caso seja observado que houve uma boa segmentação, porém com pequenos buracos ou excessos, você pode aplicar alguma função de pós-processamento: "Remover buracos", "Remover excessos" ou "Aparar bordas".'],
      ['\u2713', 'Adicione quantas imagens forem necessárias, verificando o desvio padrão do conjunto.'],
    ]
  };

  late List<FileSystemEntity> _savedFiles;

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

  void showQuickMessage(BuildContext context, String message){
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message))
    );
  }

  Future<List<String?>> pickImage(ImageSource source) async {
    XFile? imageXFile = await ImagePicker().pickImage(source: source);
    String? imagePath;
    if (imageXFile != null){
      CroppedFile? croppedImage = await ImageCropper().cropImage(
        sourcePath: imageXFile.path,
        aspectRatio: const CropAspectRatio(ratioX: 1, ratioY: 1)
      );
      imagePath = croppedImage?.path;
    }
    return [imageXFile!.path, imagePath];
  }

  Future<void> pushInfoPage(BuildContext context, String? originalPath, String? croppedPath) async {
    if (originalPath != null && croppedPath != null){
      var sampleName = Default.sampleName;
      final savedReports = _savedFiles.map((e) => e.path.split('/').last.split('.').first);
      var i = 0;
      while (savedReports.contains(sampleName)){
        sampleName = '${Default.sampleName} ($i)';
        i++;
      }
      await Navigator.push(
        context,
        MaterialPageRoute(builder: (context) => Root(originalPath: originalPath, initialPath: croppedPath, defaultSampleName: sampleName))
      ).whenComplete(() => getSavedFiles());
    }
  }

  void getSavedFiles() => getApplicationDocumentsDirectory().then(
    (dir) => Directory(dir.path).list().toList().then(
      (files) {
        files = [
          for (final file in files)
          if (file.path.split('.').last == 'pdf')
          file
        ];
        setState(() => _savedFiles=files);
      }
    )
  );

  Future<Map<String, String>> getUrlSettings() async {
    return {
      'Ip do servidor': await Default.ipAddress,
      'Porta do servidor': await Default.port
    };
  }

  void seeSettings(BuildContext context){
    getUrlSettings().then(
      (settings) => showDialog(
        context: context, 
        builder: (_) => AlertDialog(
          title: const Text('Configurações gerais'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final setting in settings.keys)
              ListTile(
                title: Text(setting),
                subtitle: TextField(
                  decoration: InputDecoration(
                    border: const UnderlineInputBorder(),
                    hintText: settings[setting]
                  ),
                  onChanged: (newValue) => settings[setting]=newValue
                ),
              )
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context), 
              child: const Text('Cancelar')
            ),
            TextButton(
              onPressed: () {
                Navigator.pop(context);
                final url = 'http://${settings['Ip do servidor']}:${settings['Porta do servidor']}';
                http.post(Uri.parse(url)).then(
                  (_){
                    Default.ipAddress = settings['Ip do servidor'];
                    Default.port = settings['Porta do servidor'];
                    showQuickMessage(context, 'Conexão estabecida com $url');
                  } ,
                  onError: (e) => showErrorMessage(context, 'Erro ao estabelecer conexão!', e.toString())
                );
              }, 
              child: const Text('Salvar')
            )
          ],
        )
      )
    );
  }

  @override
  void initState() {
    super.initState();
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp
    ]);
    _savedFiles = [];
    getSavedFiles();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text('Pellet Area Calculator'),
        actions: [
          IconButton(onPressed: () => seeSettings(context), icon: const Icon(Icons.settings))
        ],
      ),
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
              if (_savedFiles.isNotEmpty)
              Card(
                child: Column(
                  children: [
                    const Center(child: Text('Relatórios salvos', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold))),
                    for (final file in _savedFiles)
                    Card(
                      child: ListTile(
                        leading: const Icon(Icons.feed_outlined),
                        title: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(file.path.split('/').last),
                            Row(children: [
                              IconButton(onPressed: () => OpenFilex.open(file.path), icon: const Icon(Icons.remove_red_eye)),
                              IconButton(onPressed: () => file.delete().whenComplete(() => getSavedFiles()), icon: const Icon(Icons.delete))
                            ])
                          ]
                        ),
                      ) 
                    )
                  ],
                ),
              )
            ],
          ),
        )
      ),
      floatingActionButton: SpeedDial(
        icon: Icons.add,
        children: [
          SpeedDialChild(
            onTap: () => pickImage(ImageSource.camera).then(
              (paths) => pushInfoPage(context, paths[0], paths[1]),
              onError: (error) => showErrorMessage(context, 'Erro ao utilizar a câmera!', error.toString())
            ),
            child: const Icon(Icons.camera_alt_outlined)
          ),
          SpeedDialChild(
            onTap: () => pickImage(ImageSource.gallery).then(
              (paths) => pushInfoPage(context, paths[0], paths[1]),
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