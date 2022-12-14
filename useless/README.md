# О проекте
Проект Laterem - это групповой школьный проект @sp1dzsaus и @Zhur06 по разработке универсальной платформы для проведения занятий по Цифровой Электронике.
# Полезные файлы
Вся документация и остальные файлы для прочтения находятся в директории ./docs/.

Для понимания структуры проекта, рекомендуется прочесть `./docs/structure.md`. Этот файл описывает всю файловую структуру проекта.

`./TODO.md` в базовой директории отражает процесс разработки и позволяет посмотреть сделанные/запланированные фичи проекта.

## Файлы, подразумевающие возможность вмешания сторонних людей (не разработчиков)
Файлы директории ltm (laterem task modules) позволяют создавать свои задачи. Для редактирования желательно прочитать документации dew-2 и dew-3

# Инструкция по запуску сервера
* Создайте пустую папку
* Скачайте репозиторий
    * Скачайте архив (нажмите кнопку `Code` - `Download ZIP`)
    * Разархивируйте архив в папку
    
    ИЛИ
    * Откройте папку в Git Bash/консоли Visual Studio Code
    * Выполните команду

            git clone https://github.com/sp1dzsaus/laterem.git
* Запросите и перенесите файл `secret_data.py` в корневую директорию проекта. 
* Запустите сервер
    * Откройте директорию проекта через консоль (В случае с MacOS/Linux через встроенный терминал; если у вас установлена Windows, то через Bash)
    * Введите команду

            source quickrun.bash
* Зайдите на сервер
    * Зайдите на сервер по адресу, который будет написан в консоль (по умолчанию [localhost:8000]("localhost:8000"))